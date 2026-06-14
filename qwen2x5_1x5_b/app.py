import json
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException

from config import (
    ADAPTER_PATH,
    API_TITLE,
    API_VERSION,
    BASE_MODEL,
    DEVICE_MAP,
    INFERENCE_TIMEOUT_SECONDS,
    LOAD_IN_4BIT,
    LOAD_ON_STARTUP,
    MAX_INPUT_TOKENS,
    MAX_NEW_TOKENS,
    SERVICE_NAME,
    UNLOAD_AFTER_INFERENCE,
)
from schemas import InferenceRequest, InferenceResponse


app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
)

WORKER_PATH = Path(__file__).resolve().with_name("inference_worker.py")


@app.on_event("startup")
def load_model_on_startup():
    if LOAD_ON_STARTUP and not UNLOAD_AFTER_INFERENCE:
        get_model().load()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "model": get_model_info(),
    }


@app.post("/infer", response_model=InferenceResponse)
def infer(request: InferenceRequest):
    return _run_inference(request)


@app.post("/key-embedding/infer", response_model=InferenceResponse)
def infer_key_embedding(request: InferenceRequest):
    return _run_inference(request)


def _run_inference(request):
    try:
        if UNLOAD_AFTER_INFERENCE:
            return run_worker_inference(request)
        return get_model().infer(
            request.text,
            max_new_tokens=request.max_new_tokens,
            temperature=request.temperature,
            include_raw=request.include_raw,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"inference failed: {exc}") from exc


def get_model_info():
    if not UNLOAD_AFTER_INFERENCE:
        return get_model().info()
    return {
        "loaded": False,
        "base_model": BASE_MODEL,
        "adapter_path": str(ADAPTER_PATH),
        "device_map": DEVICE_MAP,
        "load_in_4bit": LOAD_IN_4BIT,
        "max_input_tokens": MAX_INPUT_TOKENS,
        "max_new_tokens": MAX_NEW_TOKENS,
        "unload_after_inference": UNLOAD_AFTER_INFERENCE,
        "worker_process": True,
    }


def get_model():
    from inference import get_model as get_in_process_model

    return get_in_process_model()


def run_worker_inference(request):
    request_payload = {
        "text": request.text,
        "max_new_tokens": request.max_new_tokens,
        "temperature": request.temperature,
        "include_raw": request.include_raw,
    }
    worker_process = subprocess.run(
        [sys.executable, str(WORKER_PATH)],
        input=json.dumps(request_payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        timeout=INFERENCE_TIMEOUT_SECONDS,
    )
    worker_payload = parse_worker_output(worker_process.stdout)
    if worker_process.returncode != 0 or not worker_payload.get("ok"):
        raise_worker_error(worker_payload, worker_process.stderr)
    return worker_payload["response"]


def parse_worker_output(worker_stdout):
    try:
        return json.loads(worker_stdout or "{}")
    except json.JSONDecodeError:
        return {
            "ok": False,
            "error_type": "worker_output_error",
            "error": "worker returned invalid json",
        }


def raise_worker_error(worker_payload, worker_stderr):
    error_type = worker_payload.get("error_type") or "inference_error"
    error_message = worker_payload.get("error") or "worker failed"
    if worker_stderr:
        error_message = f"{error_message}: {worker_stderr[-2000:]}"
    if error_type == "value_error":
        raise ValueError(error_message)
    if error_type == "file_not_found":
        raise FileNotFoundError(error_message)
    raise RuntimeError(error_message)
