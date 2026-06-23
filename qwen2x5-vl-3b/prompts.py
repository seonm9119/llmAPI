KEYVALUE_VLM_SYSTEM_PROMPT = """You are a visual document field-key extractor.
Return exactly one compact JSON object and no extra text.
Use only field labels that are visibly present in the image.
Extract keys only. Do not extract values.
Do not output coordinates, bounding boxes, polygons, ids, explanations, or confidence.
Do not invent labels from prior knowledge."""

KEYVALUE_VLM_OUTPUT_SCHEMA_TEXT = '{"keys":["visible field label"],"warnings":[]}'


def build_keyvalue_vlm_messages(image_base64):
    return [
        {
            "role": "system",
            "content": KEYVALUE_VLM_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": build_keyvalue_vlm_prompt(),
            "images": [image_base64],
        },
    ]


def build_keyvalue_vlm_prompt():
    return f"""이미지 안의 문서를 보고 보이는 key/field label만 추출하세요. 최대 20개까지만 출력하세요.

목적:
- 이미지 안의 모든 항목명, 라벨, 필드명만 찾습니다.
- 값(value)은 절대 출력하지 않습니다.

포함:
- 표 셀 안의 라벨
- 입력칸 앞 라벨
- 콜론(:)이 붙은 필드명
- 같은 라벨은 절대 반복하지 말고 한 번만 출력합니다.

제외:
- 손글씨 값
- 날짜, 금액, 이메일, 전화번호, 주소 같은 value
- 문서 제목
- 섹션 제목만 단독으로 쓰인 문구
- 긴 안내문, 설명문, 고지문
- 서명/도장 자리, (인), 체크박스 텍스트

출력 JSON:
{KEYVALUE_VLM_OUTPUT_SCHEMA_TEXT}

마크다운 코드블록 없이 JSON만 응답하세요. JSON을 닫은 뒤 즉시 멈추세요."""
