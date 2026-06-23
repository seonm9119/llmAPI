import base64
import json
import os
import re

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from prompts import build_keyvalue_vlm_messages


app = FastAPI(
    title="qwen2x5-vl-3b-api",
    version="0.4.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

OLLAMA_DEFAULT_BASE_URL = "http://ollama:11434"
OLLAMA_DEFAULT_MODEL_ID = "qwen2.5vl:3b"


@app.get("/health")
async def health():
    return {
        "service": "qwen2x5-vl-3b-api",
        "status": "ok",
        "ollama_base_url": get_ollama_base_url(),
        "model": get_ollama_model_id(),
    }


@app.post("/api/vlm/keyvalue/extract")
async def extract_keyvalue_keys(
    image: UploadFile = File(...),
    include_raw: bool = Form(False),
):
    image_bytes = await image.read()
    validate_image(image, image_bytes)

    try:
        generated_text = await call_ollama(image_bytes)
    except Exception as error:
        return {
            "status": "failed",
            "keys": [],
            "warnings": [f"Ollama VLM 호출 실패: {error}"],
            "model": get_ollama_model_id(),
        }

    parsed_payload = parse_jsonish_payload(generated_text)
    normalized_response = normalize_vlm_response(parsed_payload)
    if not parsed_payload:
        normalized_response = normalize_partial_vlm_response(generated_text)

    normalized_response["status"] = "ok" if normalized_response["keys"] else "empty"
    normalized_response["model"] = get_ollama_model_id()
    normalized_response["image"] = {
        "filename": clean_text(image.filename),
        "content_type": clean_text(image.content_type),
        "bytes": len(image_bytes),
    }

    if include_raw:
        normalized_response["raw"] = generated_text

    return normalized_response


def validate_image(image, image_bytes):
    if not image_bytes:
        raise HTTPException(status_code=400, detail="image 파일이 비어 있습니다.")

    if len(image_bytes) > get_max_image_bytes():
        raise HTTPException(status_code=413, detail="image 파일이 허용 크기를 초과했습니다.")

    content_type = clean_text(image.content_type).lower()
    if content_type and not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="image 파일만 업로드할 수 있습니다.")


async def call_ollama(image_bytes):
    image_base64 = base64.b64encode(image_bytes).decode("ascii")
    request_body = {
        "model": get_ollama_model_id(),
        "messages": build_keyvalue_vlm_messages(image_base64),
        "stream": False,
        "options": {
            "temperature": 0.0,
            "top_p": 0.8,
            "repeat_penalty": 1.2,
            "num_predict": get_num_predict(),
        },
    }

    async with httpx.AsyncClient(timeout=get_ollama_timeout_seconds()) as client:
        response = await client.post(f"{get_ollama_base_url()}/api/chat", json=request_body)
        response.raise_for_status()
        return extract_ollama_text(response.json())


def extract_ollama_text(response_payload):
    if not isinstance(response_payload, dict):
        return ""

    message_payload = response_payload.get("message")
    if isinstance(message_payload, dict):
        return clean_text(message_payload.get("content"))

    return clean_text(response_payload.get("response"))


def parse_jsonish_payload(value):
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None

    response_text = value.strip()
    if not response_text:
        return None

    if response_text.startswith("```"):
        response_text = re.sub(r"^```(?:json)?\s*", "", response_text, flags=re.I).strip()
        response_text = re.sub(r"\s*```$", "", response_text).strip()

    for candidate_text in (response_text, slice_json_object(response_text)):
        if not candidate_text:
            continue
        try:
            return json.loads(candidate_text)
        except json.JSONDecodeError:
            continue

    return None


def slice_json_object(response_text):
    start_index = response_text.find("{")
    end_index = response_text.rfind("}")
    if start_index < 0 or end_index <= start_index:
        return ""
    return response_text[start_index:end_index + 1]


def normalize_vlm_response(response_payload):
    response_payload = response_payload if isinstance(response_payload, dict) else {}
    raw_keys = response_payload.get("keys") or response_payload.get("labels") or response_payload.get("fields")
    if raw_keys is None:
        raw_keys = response_payload.get("pairs")

    return {
        "keys": normalize_key_candidates(raw_keys),
        "warnings": clean_text_list(response_payload.get("warnings")),
    }


def normalize_partial_vlm_response(generated_text):
    partial_keys = normalize_key_candidates(extract_partial_key_list(generated_text))
    warnings = []
    if partial_keys:
        warnings.append("VLM 응답 JSON을 완전히 해석하지 못해 부분 key 목록을 사용했습니다.")
    else:
        warnings.append("VLM 응답 JSON을 해석하지 못했습니다.")
    return {
        "keys": partial_keys,
        "warnings": warnings,
    }


def extract_partial_key_list(generated_text):
    if not isinstance(generated_text, str):
        return []

    key_values = []
    keys_index = generated_text.find('"keys"')
    if keys_index < 0:
        keys_index = generated_text.find("'keys'")
    if keys_index < 0:
        return []

    bracket_index = generated_text.find("[", keys_index)
    if bracket_index < 0:
        return []

    end_index = generated_text.find("]", bracket_index)
    if end_index < 0:
        end_index = len(generated_text)

    key_list_text = generated_text[bracket_index + 1:end_index]
    for key_text in re.findall(r'"([^"]{1,80})"', key_list_text):
        if is_reasonable_key_candidate(key_text):
            key_values.append(key_text)

    return key_values


def normalize_key_candidates(raw_keys):
    if not isinstance(raw_keys, list):
        return []

    key_candidates = []
    seen_keys = set()
    for raw_key in raw_keys:
        if isinstance(raw_key, dict):
            key_text = clean_text(raw_key.get("key") or raw_key.get("label") or raw_key.get("name"))
        else:
            key_text = clean_text(raw_key)
        if not key_text or not is_reasonable_key_candidate(key_text):
            continue

        normalized_key = normalize_key_text(key_text)
        if not normalized_key or normalized_key in seen_keys:
            continue

        key_candidates.append(key_text)
        seen_keys.add(normalized_key)

    return key_candidates[:get_max_keys()]


def is_reasonable_key_candidate(value):
    value = clean_text(value)
    if not value or value in ["keys", "warnings"]:
        return False
    if len(value) > 40:
        return False
    if "@" in value:
        return False
    return True


def normalize_key_text(value):
    return re.sub(r"[\s:：()（）/._,\-]+", "", clean_text(value)).lower()


def clean_text_list(values):
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return []
    return [cleaned_value for cleaned_value in (clean_text(value) for value in values) if cleaned_value]


def clean_text(value):
    return " ".join(str(value or "").split()).strip()


def get_ollama_base_url():
    return os.environ.get("OLLAMA_BASE_URL", OLLAMA_DEFAULT_BASE_URL).strip().rstrip("/")


def get_ollama_model_id():
    return (
        os.environ.get("OLLAMA_VLM_MODEL_ID")
        or os.environ.get("OLLAMA_MODEL_ID")
        or OLLAMA_DEFAULT_MODEL_ID
    ).strip() or OLLAMA_DEFAULT_MODEL_ID


def get_ollama_timeout_seconds():
    try:
        return float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "240"))
    except ValueError:
        return 240


def get_num_predict():
    try:
        return max(256, int(os.environ.get("VLM_NUM_PREDICT", "1024")))
    except ValueError:
        return 384


def get_max_keys():
    try:
        return max(1, int(os.environ.get("VLM_MAX_KEYS", os.environ.get("VLM_MAX_REGIONS", "80"))))
    except ValueError:
        return 80


def get_max_image_bytes():
    try:
        max_image_mb = max(1, int(os.environ.get("VLM_MAX_IMAGE_MB", "12")))
    except ValueError:
        max_image_mb = 12
    return max_image_mb * 1024 * 1024
