import json
import os
import re

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ollama_client import call_ollama_chat, get_ollama_base_url, get_ollama_text_model_id
from prompts import build_keyvalue_messages


app = FastAPI(
    title="qwen2x5-keyvalue-api",
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

@app.get("/health")
def health():
    return {
        "service": "qwen2x5-keyvalue-api",
        "status": "ok",
        "ollama_base_url": get_ollama_base_url(),
        "model": get_ollama_text_model_id(),
    }


@app.post("/api/keyvalue/extract")
async def extract_keyvalue_pairs(payload=Body(default=None)):
    request_payload = payload if isinstance(payload, dict) else {}
    keyvalue_candidates = normalize_keyvalue_candidates(request_payload.get("candidates"))
    image_payload = request_payload.get("image") if isinstance(request_payload.get("image"), dict) else {}
    include_raw = bool(request_payload.get("include_raw", False))

    if not keyvalue_candidates:
        return {
            "status": "empty",
            "pairs": [],
            "unmatched_keys": [],
            "warnings": ["key-value 후보가 비어 있습니다."],
        }

    limited_candidates = keyvalue_candidates[:get_max_candidates()]
    messages = build_keyvalue_messages({
        "image": normalize_image_payload(image_payload),
        "candidates": limited_candidates,
    })

    try:
        generated_text = await call_ollama_chat(messages, max_tokens=768, temperature=0.0)
    except Exception as error:
        return {
            "status": "failed",
            "pairs": [],
            "unmatched_keys": [],
            "warnings": [f"Ollama 호출 실패: {error}"],
        }

    parsed_payload = parse_jsonish_payload(generated_text)
    normalized_response = normalize_keyvalue_response(parsed_payload)
    normalized_response["status"] = "ok" if normalized_response["pairs"] else "empty"

    if len(keyvalue_candidates) > len(limited_candidates):
        normalized_response["warnings"].append(
            f"key-value 후보가 많아 앞 {len(limited_candidates)}개만 Ollama에 전달했습니다."
        )
    if not parsed_payload:
        normalized_response["warnings"].append("Ollama 응답 JSON을 해석하지 못했습니다.")
    if include_raw:
        normalized_response["raw"] = generated_text

    return normalized_response


def get_max_candidates():
    try:
        return max(10, int(os.environ.get("KEYVALUE_MAX_CANDIDATES", "60")))
    except ValueError:
        return 60


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


def normalize_keyvalue_response(response_payload):
    response_payload = response_payload if isinstance(response_payload, dict) else {}
    return {
        "pairs": normalize_keyvalue_pairs(response_payload.get("pairs")),
        "unmatched_keys": clean_text_list(response_payload.get("unmatched_keys")),
        "warnings": clean_text_list(response_payload.get("warnings")),
    }


def normalize_keyvalue_pairs(raw_pairs):
    if not isinstance(raw_pairs, list):
        return []

    keyvalue_pairs = []
    for raw_pair in raw_pairs:
        if not isinstance(raw_pair, dict):
            continue

        key_text = clean_text(raw_pair.get("key"))
        value_text = clean_text(raw_pair.get("value"))
        if not key_text or not value_text:
            continue

        keyvalue_pairs.append({
            "key": key_text,
            "value": value_text,
            "key_ocr_ids": clean_text_list(raw_pair.get("key_ocr_ids") or raw_pair.get("keyBoxIds")),
            "value_ocr_ids": clean_text_list(raw_pair.get("value_ocr_ids") or raw_pair.get("valueBoxIds")),
            "relation": clean_text(raw_pair.get("relation")) or "unknown",
            "confidence": normalize_confidence(raw_pair.get("confidence")),
            "reason": clean_text(raw_pair.get("reason")),
        })

    return keyvalue_pairs


def normalize_keyvalue_candidates(raw_candidates):
    if not isinstance(raw_candidates, list):
        return []

    keyvalue_candidates = []
    for raw_candidate in raw_candidates:
        if not isinstance(raw_candidate, dict):
            continue
        candidate_id = clean_text(raw_candidate.get("id"))
        key_text = clean_text(raw_candidate.get("key_text") or raw_candidate.get("key"))
        value_text = clean_text(raw_candidate.get("value_text") or raw_candidate.get("value"))
        if not candidate_id or not key_text or not value_text:
            continue

        keyvalue_candidates.append({
            "id": candidate_id,
            "key_text": key_text,
            "value_text": value_text,
            "key_ocr_ids": clean_text_list(raw_candidate.get("key_ocr_ids")),
            "value_ocr_ids": clean_text_list(raw_candidate.get("value_ocr_ids")),
            "relation": clean_text(raw_candidate.get("relation")) or "unknown",
            "confidence": normalize_confidence(raw_candidate.get("confidence")),
            "key_polygon": normalize_polygon(raw_candidate.get("key_polygon")),
            "value_polygons": normalize_polygons(raw_candidate.get("value_polygons")),
            "key_bbox": normalize_bbox(raw_candidate.get("key_bbox")),
            "value_bbox": normalize_bbox(raw_candidate.get("value_bbox")),
            "source": clean_text(raw_candidate.get("source")),
        })

    return keyvalue_candidates


def normalize_polygons(raw_polygons):
    if not isinstance(raw_polygons, list):
        return []
    return [
        polygon
        for polygon in (normalize_polygon(raw_polygon) for raw_polygon in raw_polygons)
        if polygon
    ]


def normalize_polygon(raw_polygon):
    if not isinstance(raw_polygon, list):
        return []

    polygon = []
    for raw_point in raw_polygon:
        if not isinstance(raw_point, list) or len(raw_point) < 2:
            continue
        try:
            polygon.append([round(float(raw_point[0]), 2), round(float(raw_point[1]), 2)])
        except (TypeError, ValueError):
            continue
    return polygon if len(polygon) >= 4 else []


def normalize_bbox(raw_bbox):
    if not isinstance(raw_bbox, list) or len(raw_bbox) < 4:
        return []
    try:
        return [round(float(value), 2) for value in raw_bbox[:4]]
    except (TypeError, ValueError):
        return []


def normalize_image_payload(image_payload):
    return {
        "filename": clean_text(image_payload.get("filename")),
        "width": image_payload.get("width"),
        "height": image_payload.get("height"),
    }


def clean_text_list(values):
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return []

    clean_values = []
    seen_values = set()
    for value in values:
        clean_value = clean_text(value)
        if not clean_value or clean_value in seen_values:
            continue
        clean_values.append(clean_value)
        seen_values.add(clean_value)
    return clean_values


def clean_text(raw_value):
    return " ".join(str(raw_value or "").split()).strip()


def normalize_confidence(raw_confidence):
    try:
        confidence = float(raw_confidence)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))
