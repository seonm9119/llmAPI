KEYVALUE_SYSTEM_PROMPT = """You are a document key-value extraction engine.
Use only the provided key-value candidates.
Return exactly one JSON object and no extra text.
Do not invent keys or values that are not supported by OCR text."""

KEYVALUE_OUTPUT_SCHEMA_TEXT = (
    '{"pairs":[{"key":"field label","value":"field value",'
    '"key_ocr_ids":["ocr-1"],"value_ocr_ids":["ocr-2"],'
    '"relation":"right","confidence":0.91,"reason":"short reason"}],'
    '"unmatched_keys":[],"warnings":[]}'
)


def build_keyvalue_messages(keyvalue_payload):
    return [
        {
            "role": "system",
            "content": KEYVALUE_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": build_keyvalue_user_prompt(keyvalue_payload),
        },
    ]


def build_keyvalue_user_prompt(keyvalue_payload):
    image_payload = keyvalue_payload.get("image") if isinstance(keyvalue_payload.get("image"), dict) else {}
    candidate_lines = build_candidate_lines(keyvalue_payload.get("candidates"))

    return f"""문서 OCR에서 미리 추린 key-value 후보를 검수해서 최종 pair만 남기세요.

규칙:
- 후보의 key/value text와 OCR id만 사용하세요.
- 안내문, 섹션 제목, 불완전한 값은 제외하세요.
- value가 여러 조각이면 자연스럽게 이어 붙이세요.
- OCR 오탈자는 추정 보정하지 말고 원문을 유지하세요.
- confidence는 0.0~1.0 숫자입니다.

출력 JSON:
{KEYVALUE_OUTPUT_SCHEMA_TEXT}

image={image_payload.get("filename", "")}, size={image_payload.get("width", "")}x{image_payload.get("height", "")}

candidate format:
id|relation|key_text|value_text|key_ocr_ids|value_ocr_ids|key_polygon|value_polygons

candidates:
{candidate_lines}

JSON만 응답하세요."""


def build_candidate_lines(raw_candidates):
    if not isinstance(raw_candidates, list):
        return ""

    candidate_lines = []
    for candidate in raw_candidates:
        if not isinstance(candidate, dict):
            continue

        candidate_lines.append("|".join([
            clean_field(candidate.get("id")),
            clean_field(candidate.get("relation")),
            clean_field(candidate.get("key_text")),
            clean_field(candidate.get("value_text")),
            ",".join(clean_list(candidate.get("key_ocr_ids"))),
            ",".join(clean_list(candidate.get("value_ocr_ids"))),
            compact_polygon(candidate.get("key_polygon")),
            ";".join(compact_polygon(polygon) for polygon in candidate.get("value_polygons") or []),
        ]))

    return "\n".join(candidate_lines)


def compact_polygon(polygon):
    if not isinstance(polygon, list):
        return ""

    coordinates = []
    for point in polygon:
        if not isinstance(point, list) or len(point) < 2:
            continue
        try:
            coordinates.append(str(int(round(float(point[0])))))
            coordinates.append(str(int(round(float(point[1])))))
        except (TypeError, ValueError):
            continue
    return ",".join(coordinates)


def clean_list(values):
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return []
    return [clean_field(value) for value in values if clean_field(value)]


def clean_field(value):
    return " ".join(str(value or "").replace("|", " ").split()).strip()
