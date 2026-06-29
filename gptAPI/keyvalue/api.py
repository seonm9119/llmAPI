import base64
import json
import mimetypes
import re

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from client import get_openai_client
from config import GPT_MODEL
from prompts import KEYVALUE_SYSTEM_PROMPT, build_keyvalue_user_prompt


app = FastAPI(
    title="gpt-keyvalue-api",
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

KEYVALUE_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["keys", "warnings"],
    "properties": {
        "keys": {
            "type": "array",
            "items": {"type": "string"},
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}


@app.get("/api/gpt/keyvalue/health")
def health():
    return {
        "service": "gpt-keyvalue-api",
        "status": "ok",
        "provider": "openai",
        "model": GPT_MODEL,
    }


@app.post("/api/gpt/keyvalue/extract")
async def extract_keyvalue_keys(
    image: UploadFile = File(...),
    include_raw: bool = Form(False),
):
    image_bytes = await image.read()
    validate_image(image, image_bytes)

    try:
        gpt_response, raw_text = request_gpt_keyvalue(image.filename, image.content_type, image_bytes)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"OpenAI GPT 호출 실패: {error}")

    normalized_response = normalize_gpt_keyvalue_response(gpt_response)
    normalized_response["status"] = "ok" if normalized_response["keys"] else "empty"
    normalized_response["model"] = GPT_MODEL
    normalized_response["image"] = {
        "filename": clean_text(image.filename),
        "content_type": clean_text(image.content_type),
        "bytes": len(image_bytes),
    }

    if include_raw:
        normalized_response["raw"] = raw_text

    return normalized_response


def validate_image(image, image_bytes):
    if not image_bytes:
        raise HTTPException(status_code=400, detail="image 파일이 비어 있습니다.")

    content_type = clean_text(image.content_type).lower()
    if content_type and not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="image 파일만 업로드할 수 있습니다.")


def request_gpt_keyvalue(image_filename, content_type, image_bytes):
    client = get_openai_client()
    image_data_url = build_image_data_url(image_filename, content_type, image_bytes)
    response = client.responses.create(
        model=GPT_MODEL,
        input=[
            {
                "role": "system",
                "content": KEYVALUE_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": build_keyvalue_user_prompt(clean_text(image_filename)),
                    },
                    {
                        "type": "input_image",
                        "image_url": image_data_url,
                        "detail": "high",
                    },
                ],
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "gpt_keyvalue_keys",
                "strict": True,
                "schema": KEYVALUE_RESPONSE_SCHEMA,
            }
        },
    )

    raw_text = getattr(response, "output_text", "") or ""
    if not raw_text:
        raise RuntimeError("OpenAI response did not include output_text.")

    return json.loads(raw_text), raw_text


def build_image_data_url(image_filename, content_type, image_bytes):
    safe_content_type = clean_text(content_type)
    if not safe_content_type:
        safe_content_type = mimetypes.guess_type(clean_text(image_filename))[0] or "image/png"

    image_base64 = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{safe_content_type};base64,{image_base64}"


def normalize_gpt_keyvalue_response(response_payload):
    response_payload = response_payload if isinstance(response_payload, dict) else {}

    return {
        "keys": normalize_key_candidates(response_payload.get("keys")),
        "warnings": clean_text_list(response_payload.get("warnings")),
    }


def normalize_key_candidates(raw_keys):
    if not isinstance(raw_keys, list):
        return []

    key_candidates = []
    seen_keys = set()
    for raw_key in raw_keys:
        key_text = clean_text(raw_key.get("key") if isinstance(raw_key, dict) else raw_key)
        if not key_text or not is_reasonable_key_candidate(key_text):
            continue

        normalized_key = normalize_key_text(key_text)
        if not normalized_key or normalized_key in seen_keys:
            continue

        key_candidates.append(key_text)
        seen_keys.add(normalized_key)

    return key_candidates[:20]


def is_reasonable_key_candidate(key_text):
    key_text = clean_text(key_text)
    if not key_text or key_text in ["keys", "warnings"]:
        return False
    if len(key_text) > 40:
        return False
    if "@" in key_text:
        return False
    return True


def normalize_key_text(key_text):
    return re.sub(r"[\s:：()（）/._,\-]+", "", clean_text(key_text)).lower()


def clean_text_list(values):
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return []

    clean_values = []
    seen_values = set()
    for raw_value in values:
        clean_value = clean_text(raw_value)
        if not clean_value or clean_value in seen_values:
            continue
        clean_values.append(clean_value)
        seen_values.add(clean_value)
    return clean_values


def clean_text(raw_value):
    return " ".join(str(raw_value or "").split()).strip()
