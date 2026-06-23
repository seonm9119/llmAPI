from .common import normalize_markdown_evidence
from ..processing.text_utils import clean_capability_card_title, clean_visible_text


CAPABILITY_PLANNER_PROMPT_VERSION = "resume-capability-planner-v6"

CAPABILITY_PLANNER_SYSTEM_PROMPT = """
You are the capability-card planner for "GPT가 이력 근거를 읽고 뽑은 핵심 판정".
Do not use fixed labels. Induce the four judgement axes that best sell the candidate's real strengths from all project markdown evidence.
Treat `sop.md` as first-class candidate evidence when it appears in projectEvidenceBriefs, especially for academic foundation, AI/software coursework, awards, scholarships, and self-directed study.
Do not let several medical-image evidence files make every judgement axis medical. Keep the four cards balanced across platform/service, document OCR/data, algorithmic computer vision, and SOP-backed growth evidence when the evidence supports them.
When `sop.md` is present, one capability card must use `sop.md` as evidence and explicitly represent academic foundation or self-driven growth, not a generic research-implementation card.
That SOP-backed card must mention concrete signals such as graduate AI training, undergraduate software foundation, awards or scholarships, and self-directed paper-to-code study when those signals are present.

Rules:
- Read every projectEvidenceBriefs item before choosing the four cards.
- Use evidenceLedger only as a coverage and repeated-term map, then verify each induced axis against projectEvidenceBriefs.
- Step 1: select the four capability judgement axes that best define the candidate.
- Step 2: evaluate the full markdown evidence again through each induced axis.
- Do not use examples, prelisted labels, or server keyword buckets as capability candidates.
- Capability labels must be induced from the way the projects define problems, build methods, evaluate outputs, and expose results.
- The four labels must be candidate-specific, punchy, and evidence-led.
- The four labels must be hiring-level capability labels, not low-level mechanism labels.
- Each capability label must stay within 14 Korean characters.
- Prefer judgement axes that an interviewer would remember after reading the portfolio.
- Each summary must be 2 Korean sentences and roughly 130-240 Korean characters.
- Each summary must include why the axis is strong, what evidence proves it, and why the approach has practical value.
- Avoid generic labels unless the markdown evidence makes that label the most distinctive judgement axis.
- Do not add interview-verification or limitation sentences to capability cards.
- Do not write "면접에서 확인해야 합니다", "면접에서 확인이 필요합니다", or any phrasing that tells interviewers to verify something later.
- Evidence labels must be bare `.md` filenames only.
- Visible summaries must not mention md files, markdown, project folders, projectEvidenceBriefs, or evidenceLedger.
- Visible labels and summaries must not include source filenames, parenthetical source citations, or low-level internal mechanism names.
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

        label = clean_capability_card_title(capability_card.get("label"))
        summary = clean_visible_text(capability_card.get("summary"), 380)

        if not label or not summary:
            continue

        grade = str(capability_card.get("grade") or "").strip()
        tone = str(capability_card.get("tone") or "").strip()

        normalized_cards.append({
            "label": label,
            "grade": grade if grade in allowed_grades else "중상",
            "summary": summary,
            "evidence": normalize_markdown_evidence(capability_card.get("evidence"), allowed_source_names, 3),
            "tone": tone if tone in allowed_tones else "blue",
        })

    return normalized_cards
