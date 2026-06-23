import os

import httpx


OLLAMA_DEFAULT_BASE_URL = "http://ollama:11434"
OLLAMA_DEFAULT_TEXT_MODEL_ID = "qwen2.5:7b"


def get_ollama_base_url():
    return (
        os.environ.get("OLLAMA_BASE_URL")
        or os.environ.get("QWEN_BASE_URL")
        or OLLAMA_DEFAULT_BASE_URL
    ).strip().rstrip("/")


def get_ollama_text_model_id():
    return (
        os.environ.get("OLLAMA_TEXT_MODEL_ID")
        or os.environ.get("QWEN_MODEL_ID")
        or OLLAMA_DEFAULT_TEXT_MODEL_ID
    ).strip() or OLLAMA_DEFAULT_TEXT_MODEL_ID


def get_ollama_text_timeout_seconds():
    timeout_seconds = (
        os.environ.get("OLLAMA_TEXT_TIMEOUT_SECONDS")
        or os.environ.get("QWEN_TIMEOUT_SECONDS")
        or os.environ.get("OLLAMA_TIMEOUT_SECONDS")
        or "180"
    ).strip()
    try:
        return float(timeout_seconds)
    except ValueError:
        return 180


async def call_ollama_chat(messages, max_tokens=768, temperature=0.0):
    request_body = {
        "model": get_ollama_text_model_id(),
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    async with httpx.AsyncClient(timeout=get_ollama_text_timeout_seconds()) as client:
        response = await client.post(
            f"{get_ollama_base_url()}/api/chat",
            json=request_body,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return extract_ollama_text(response.json())


def extract_ollama_text(response_payload):
    if not isinstance(response_payload, dict):
        return ""

    message_payload = response_payload.get("message")
    if isinstance(message_payload, dict):
        return str(message_payload.get("content") or "").strip()

    response_text = response_payload.get("response")
    if isinstance(response_text, str):
        return response_text.strip()

    choices_payload = response_payload.get("choices")
    if isinstance(choices_payload, list) and choices_payload:
        first_choice_payload = choices_payload[0] if isinstance(choices_payload[0], dict) else {}
        message_payload = first_choice_payload.get("message")
        if isinstance(message_payload, dict):
            return str(message_payload.get("content") or "").strip()
        return str(first_choice_payload.get("text") or "").strip()

    for field_name in ("content", "text", "message"):
        field_payload = response_payload.get(field_name)
        if isinstance(field_payload, str):
            return field_payload.strip()
        if isinstance(field_payload, dict):
            nested_content = field_payload.get("content")
            if isinstance(nested_content, str):
                return nested_content.strip()

    return ""
