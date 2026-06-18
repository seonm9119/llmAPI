from .common import normalize_markdown_evidence


CAPABILITY_PLANNER_PROMPT_VERSION = "resume-capability-planner-v2"

CAPABILITY_PLANNER_SYSTEM_PROMPT = """
You are the capability-card planner for "GPT가 이력 근거를 읽고 뽑은 핵심 판정".
Do not use fixed labels. Choose the four judgement axes that best sell the candidate's real strengths from all project markdown evidence.

Rules:
- Read every projectEvidenceBriefs item before choosing the four cards.
- Use evidenceLedger first to see repeated signals, then verify each chosen axis against projectEvidenceBriefs.
- Step 1: select the four capability judgement axes that best define the candidate.
- Step 2: evaluate the full markdown evidence again through each selected axis.
- The four labels must be candidate-specific, punchy, and evidence-led.
- Prefer judgement axes that an interviewer would remember after reading the portfolio.
- Each summary must be 2 Korean sentences and roughly 130-240 Korean characters.
- Each summary must include why the axis is strong, what evidence proves it, and what still needs interview verification.
- Avoid generic labels such as "문제해결능력" unless the markdown evidence makes that the most distinctive judgement axis.
- Include limitations only where they sharpen the evaluation.
- Evidence labels must be bare `.md` filenames only.
- Visible summaries must not mention md files, markdown, project folders, projectEvidenceBriefs, or evidenceLedger.
- Do not call the candidate "이 사람"; use "지원자" sparingly or write with the capability as the sentence subject.
- Do not call the candidate "시니어".
- Return only the requested JSON object.
""".strip()

CAPABILITY_PLANNER_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["capabilityCards"],
    "properties": {
        "capabilityCards": {
            "type": "array",
            "minItems": 4,
            "maxItems": 4,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["label", "grade", "summary", "evidence", "tone"],
                "properties": {
                    "label": {"type": "string"},
                    "grade": {
                        "type": "string",
                        "enum": ["상", "중상", "중", "하"],
                    },
                    "summary": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 3,
                        "items": {"type": "string"},
                    },
                    "tone": {
                        "type": "string",
                        "enum": ["blue", "green", "amber", "coral"],
                    },
                },
            },
        },
    },
}


def normalize_capability_plan(capability_plan, allowed_source_names=None):
    if not isinstance(capability_plan, dict):
        return []

    capability_cards = capability_plan.get("capabilityCards")

    if not isinstance(capability_cards, list):
        return []

    normalized_cards = []
    allowed_grades = {"상", "중상", "중", "하"}
    allowed_tones = {"blue", "green", "amber", "coral"}

    for capability_card in capability_cards[:4]:
        if not isinstance(capability_card, dict):
            continue

        label = str(capability_card.get("label") or "").strip()
        summary = str(capability_card.get("summary") or "").strip()

        if not label or not summary:
            continue

        grade = str(capability_card.get("grade") or "").strip()
        tone = str(capability_card.get("tone") or "").strip()

        normalized_cards.append({
            "label": label[:24],
            "grade": grade if grade in allowed_grades else "중상",
            "summary": summary[:380],
            "evidence": normalize_markdown_evidence(capability_card.get("evidence"), allowed_source_names, 3),
            "tone": tone if tone in allowed_tones else "blue",
        })

    return normalized_cards
