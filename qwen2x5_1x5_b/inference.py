import ast
import gc
import json
import threading
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from config import (
    ADAPTER_PATH,
    AXES,
    BASE_MODEL,
    DEVICE_MAP,
    LOAD_IN_4BIT,
    MAX_INPUT_TOKENS,
    MAX_NEW_TOKENS,
    SYSTEM_PROMPT,
    TEMPERATURE,
    TOP_P,
    UNLOAD_AFTER_INFERENCE,
    build_user_prompt,
)
from schemas import unknown_axes


class KeyEmbeddingModel:
    def __init__(self):
        self.adapter_path = Path(ADAPTER_PATH)
        self.base_model = BASE_MODEL
        self.tokenizer = None
        self.model = None
        self._generate_lock = threading.Lock()

    @property
    def loaded(self):
        return self.model is not None and self.tokenizer is not None

    def load(self):
        if self.loaded:
            return
        if not self.adapter_path.exists():
            raise FileNotFoundError(f"adapter path not found: {self.adapter_path}")

        self.base_model = self._resolve_base_model()
        self.tokenizer = AutoTokenizer.from_pretrained(str(self.adapter_path), trust_remote_code=False)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "left"

        model_kwargs = {
            "device_map": DEVICE_MAP,
            "trust_remote_code": False,
        }
        if self._should_load_4bit():
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
            model_kwargs["torch_dtype"] = torch.float16
        else:
            model_kwargs["torch_dtype"] = torch.float16 if torch.cuda.is_available() else torch.float32

        base_model = AutoModelForCausalLM.from_pretrained(self.base_model, **model_kwargs)
        self.model = PeftModel.from_pretrained(base_model, str(self.adapter_path))
        self.model.eval()

    def unload(self):
        if self.model is None and self.tokenizer is None:
            return

        loaded_model = self.model
        loaded_tokenizer = self.tokenizer
        self.model = None
        self.tokenizer = None
        del loaded_model
        del loaded_tokenizer
        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            try:
                torch.cuda.ipc_collect()
            except Exception:
                pass

    def infer(self, text, *, max_new_tokens=None, temperature=None, include_raw=False):
        cleaned_text = str(text or "").strip()
        if not cleaned_text:
            raise ValueError("text is empty")

        with self._generate_lock:
            self.load()
            assert self.model is not None
            assert self.tokenizer is not None

            try:
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(cleaned_text)},
                ]
                prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                inputs = self.tokenizer(
                    prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=MAX_INPUT_TOKENS,
                )
                inputs = {key: value.to(self._input_device()) for key, value in inputs.items()}

                generation_temperature = TEMPERATURE if temperature is None else temperature
                generation_kwargs = {
                    "max_new_tokens": max_new_tokens or MAX_NEW_TOKENS,
                    "do_sample": generation_temperature > 0,
                    "pad_token_id": self.tokenizer.eos_token_id,
                    "eos_token_id": self.tokenizer.eos_token_id,
                }
                if generation_temperature > 0:
                    generation_kwargs["temperature"] = generation_temperature
                    generation_kwargs["top_p"] = TOP_P

                started_at = time.perf_counter()
                with torch.inference_mode():
                    output_ids = self.model.generate(**inputs, **generation_kwargs)
                elapsed_ms = int((time.perf_counter() - started_at) * 1000)

                generated_ids = output_ids[0][inputs["input_ids"].shape[-1] :]
                raw_output = self.tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
            finally:
                if UNLOAD_AFTER_INFERENCE:
                    self.unload()

        parsed_payload = parse_json_object_from_text(raw_output)
        response_warnings = []
        if parsed_payload is None:
            response_warnings.append("model_output_json_parse_failed")
            normalized_axes = unknown_axes()
        else:
            normalized_axes = normalize_target_payload(parsed_payload)

        inference_response = {
            **normalized_axes,
            "warnings": response_warnings,
        }
        if include_raw:
            inference_response["raw_output"] = raw_output
            inference_response["elapsed_ms"] = elapsed_ms
        return inference_response

    def info(self):
        return {
            "loaded": self.loaded,
            "base_model": self.base_model,
            "adapter_path": str(self.adapter_path),
            "device_map": DEVICE_MAP,
            "load_in_4bit": LOAD_IN_4BIT,
            "unload_after_inference": UNLOAD_AFTER_INFERENCE,
            "cuda_available": torch.cuda.is_available(),
        }

    def _input_device(self):
        assert self.model is not None
        model_device = getattr(self.model, "device", None)
        if model_device is not None:
            return torch.device(model_device)
        return next(self.model.parameters()).device

    def _resolve_base_model(self):
        adapter_config_path = self.adapter_path / "adapter_config.json"
        if not adapter_config_path.is_file():
            return self.base_model
        try:
            adapter_config = json.loads(adapter_config_path.read_text(encoding="utf-8"))
        except Exception:
            return self.base_model
        return str(adapter_config.get("base_model_name_or_path") or self.base_model)

    def _should_load_4bit(self):
        if LOAD_IN_4BIT in {"1", "true", "yes", "on"}:
            return True
        if LOAD_IN_4BIT in {"0", "false", "no", "off"}:
            return False
        return torch.cuda.is_available()


def parse_json_object_from_text(text):
    payload = str(text or "").strip()
    if not payload:
        return None

    payload = payload.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    if payload.startswith("```"):
        payload = payload.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    parsed_payload = _try_parse_json_mapping(payload)
    if parsed_payload is not None:
        return parsed_payload

    decoder = json.JSONDecoder()
    for start_index, char in enumerate(payload):
        if char != "{":
            continue
        try:
            parsed_payload, end_index = decoder.raw_decode(payload[start_index:])
        except Exception:
            continue
        if isinstance(parsed_payload, dict):
            reparsed_payload = _try_parse_json_mapping(payload[start_index : start_index + end_index])
            return reparsed_payload or parsed_payload

    first_brace = payload.find("{")
    last_brace = payload.rfind("}")
    if first_brace >= 0 and last_brace > first_brace:
        return _try_parse_json_mapping(payload[first_brace : last_brace + 1])
    return None


def _try_parse_json_mapping(candidate):
    candidate = str(candidate or "").strip()
    if not candidate:
        return None
    for candidate_payload in (candidate, _remove_trailing_commas(candidate)):
        try:
            parsed_payload = json.loads(candidate_payload)
            if isinstance(parsed_payload, dict):
                return parsed_payload
        except Exception:
            pass
    try:
        parsed_payload = ast.literal_eval(_remove_trailing_commas(candidate))
        if isinstance(parsed_payload, dict):
            return parsed_payload
    except Exception:
        pass
    return None


def _remove_trailing_commas(candidate):
    return candidate.replace(",\n}", "\n}").replace(",}", "}").replace(",\n]", "\n]").replace(",]", "]")


def normalize_target_payload(raw_target):
    return {
        axis: normalize_axis_target(raw_target.get(axis))
        for axis in AXES
    }


def normalize_axis_target(raw_axis_target):
    raw_axis_target = raw_axis_target if isinstance(raw_axis_target, dict) else {}
    axis_key = clean_text(raw_axis_target.get("key")) or "unknown"
    signals = clean_text_list(raw_axis_target.get("signals"))
    if axis_key == "unknown":
        signals = []
    return {
        "key": axis_key,
        "signals": signals,
    }


def clean_text(raw_text):
    return " ".join(str(raw_text or "").replace("\r", "\n").split()).strip()


def clean_text_list(raw_signals):
    if isinstance(raw_signals, str):
        raw_signals = [raw_signals]
    if not isinstance(raw_signals, list):
        return []

    clean_signals = []
    seen_signals = set()
    for raw_signal in raw_signals:
        clean_signal = clean_text(raw_signal)
        if not clean_signal or clean_signal in seen_signals:
            continue
        clean_signals.append(clean_signal)
        seen_signals.add(clean_signal)
    return clean_signals


_model = KeyEmbeddingModel()


def get_model():
    return _model
