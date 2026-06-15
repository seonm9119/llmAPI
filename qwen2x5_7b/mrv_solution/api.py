import os
import re

import httpx
from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from prompts import get_prompt_definition


app = FastAPI(
    title="qwen2x5-mrv-solution-api",
    version="0.1.0",
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

EMPTY_VALUE = "—"
QWEN_DEFAULT_BASE_URL = "http://qwen2x5-7b:8000"


@app.get("/health")
def health():
    return {
        "service": "qwen2x5-mrv-solution-api",
        "status": "ok",
        "qwen_base_url": get_qwen_base_url(),
    }


@app.post("/api/mrv-solution/llm")
async def resolve_mrv_solution_llm(payload=Body(default=None)):
    request_payload = payload if isinstance(payload, dict) else {}
    tag = request_payload.get("tag") or ""
    db_context = request_payload.get("db_context") or {}
    if not isinstance(db_context, dict):
        db_context = {}

    field = parse_llm_field(tag)
    prompt_key, prompt_definition = get_prompt_definition(field)
    ref_keys = parse_llm_ref_keys(tag, prompt_definition["refs"])
    prompt_text = context_to_prompt_text(db_context, ref_keys, prompt_definition.get("labels", {}))
    messages = [
        {"role": "system", "content": prompt_definition["system"]},
        {"role": "user", "content": f"{prompt_definition['instruction']}\n\n{prompt_text}"},
    ]

    try:
        generated_text = await call_qwen(
            messages,
            max_tokens=prompt_definition.get("max_tokens", 512),
            temperature=prompt_definition.get("temperature", 0.3),
        )
    except Exception as error:
        return {
            "status": "failed",
            "field": field,
            "prompt_key": prompt_key,
            "value": f"LLM 실패: {error}",
        }

    response_text = (generated_text or "").strip()
    if prompt_definition.get("single_line"):
        response_text = " ".join(response_text.split())

    return {
        "status": "ok" if response_text else "empty",
        "field": field,
        "prompt_key": prompt_key,
        "value": response_text or EMPTY_VALUE,
    }


def get_qwen_base_url():
    return os.environ.get("QWEN_BASE_URL", QWEN_DEFAULT_BASE_URL).strip().rstrip("/")


def get_qwen_timeout_seconds():
    timeout_seconds = os.environ.get("QWEN_TIMEOUT_SECONDS", "180").strip()
    try:
        return float(timeout_seconds)
    except ValueError:
        return 180


async def call_qwen(messages, max_tokens=1400, temperature=0.2):
    request_body = {
        "model": os.environ.get("QWEN_MODEL_ID", "qwen2.5-7b"),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=get_qwen_timeout_seconds()) as client:
        response = await client.post(
            f"{get_qwen_base_url()}/v1/chat/completions",
            json=request_body,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return extract_llm_text(response.json())


def extract_llm_text(response_payload):
    if not isinstance(response_payload, dict):
        return ""

    choices = response_payload.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            if isinstance(message, dict):
                return str(message.get("content") or "").strip()
            return str(first_choice.get("text") or "").strip()

    for key in ("content", "response", "text", "message"):
        candidate_content = response_payload.get(key)
        if isinstance(candidate_content, str):
            return candidate_content.strip()
        if isinstance(candidate_content, dict):
            nested_content = candidate_content.get("content")
            if isinstance(nested_content, str):
                return nested_content.strip()

    return ""


def parse_llm_field(tag):
    tag = normalize_llm_tag(tag)
    match = re.search(r"\{\{llm:([a-zA-Z0-9_]+)", tag)
    return match.group(1) if match else ""


def parse_llm_ref_keys(tag, default_keys):
    tag = normalize_llm_tag(tag)
    match = re.search(r"\|ref=([^}|]+)", tag)
    if not match:
        return list(default_keys)
    keys = []
    for part in re.split(r"[,;\s]+", match.group(1)):
        key = part.strip()
        if not key:
            continue
        if key.startswith("db:"):
            key = key[3:]
        if key:
            keys.append(key)
    return keys if keys else list(default_keys)


def normalize_llm_tag(tag):
    return str(tag).replace("\u200b", "").replace("\ufeff", "")


def context_to_prompt_text(db_context, ref_keys, labels):
    lines = []
    for key in ref_keys:
        context_value = get_context_value(db_context, key)
        if context_value and context_value != EMPTY_VALUE:
            short_key = key.split(".")[-1]
            label = labels.get(key) or labels.get(short_key) or short_key
            lines.append(f"- {label}: {context_value}")
    return "\n".join(lines) if lines else "(제공된 값 없음)"


def get_context_value(db_context, key):
    key = clean_value(key)
    if key.startswith("db:"):
        key = key[3:]
    raw_context_value = db_context.get(key)
    if raw_context_value is None and "." in key:
        raw_context_value = db_context.get(key.split(".")[-1])
    if raw_context_value is None:
        return EMPTY_VALUE
    context_text = str(raw_context_value).strip()
    return context_text or EMPTY_VALUE


def clean_value(raw_value):
    if raw_value is None:
        return ""
    return str(raw_value).strip()
