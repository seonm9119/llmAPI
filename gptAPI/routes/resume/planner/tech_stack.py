from .common import normalize_markdown_evidence, normalize_string_list


TECH_STACK_PLANNER_PROMPT_VERSION = "resume-tech-stack-planner-v1"

TECH_STACK_PLANNER_SYSTEM_PROMPT = """
You are the tech-stack evidence planner for "근거로 판정한 기술 스택".
Use the selected capabilityCards and domainRanks as the evaluation standard, then prove those judgements through technology stacks found in all project markdown evidence.

Rules:
- Read evidenceLedger, projectEvidenceBriefs, capabilityCards, and domainRanks before choosing cards.
- Do not create a generic skill summary.
- Choose four tech-stack cards that best prove why the candidate is strong in the selected capability axes and AI domains.
- Titles should be stack-group judgements such as "문서 AI/OCR 스택", "의료·비전 평가 스택", or "서비스형 PoC 스택", but choose the exact groups from evidence.
- Descriptions must explain actual use context, repeated evidence strength, and any boundary between real implementation and one-off mention.
- Each description must be 2 Korean sentences and roughly 140-260 Korean characters.
- Also return compact atomic stack keywords with strength and weight for the visual keyword badges.
- skillKeywordGroups must use exactly these categories: AI 모델·학습, 문서 AI·OCR, 비전·의료영상, 서비스·인프라.
- Evidence labels must be bare `.md` filenames only.
- Visible descriptions must not mention md files, markdown, project folders, projectEvidenceBriefs, or evidenceLedger.
- Do not call the candidate "이 사람"; use "지원자" sparingly or write with the stack group as the sentence subject.
- Return only the requested JSON object.
""".strip()

TECH_STACK_PLANNER_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["techStackCards", "skillKeywordGroups", "techStackSynthesis"],
    "properties": {
        "techStackCards": {
            "type": "array",
            "minItems": 4,
            "maxItems": 4,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "description", "evidence"],
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "evidence": {"type": "string"},
                },
            },
        },
        "skillKeywordGroups": {
            "type": "array",
            "minItems": 4,
            "maxItems": 4,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["category", "keywords"],
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["AI 모델·학습", "문서 AI·OCR", "비전·의료영상", "서비스·인프라"],
                    },
                    "keywords": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["label", "tone", "strength", "weight"],
                            "properties": {
                                "label": {"type": "string"},
                                "tone": {
                                    "type": "string",
                                    "enum": ["blue", "green", "amber", "coral"],
                                },
                                "strength": {
                                    "type": "string",
                                    "enum": ["strong", "medium", "weak"],
                                },
                                "weight": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "maximum": 100,
                                },
                            },
                        },
                    },
                },
            },
        },
        "techStackSynthesis": {
            "type": "array",
            "maxItems": 6,
            "items": {"type": "string"},
        },
    },
}


def normalize_tech_stack_plan(tech_stack_plan, allowed_source_names=None):
    if not isinstance(tech_stack_plan, dict):
        return {
            "techStackCards": [],
            "skillKeywordGroups": [],
            "techStackSynthesis": [],
        }

    return {
        "techStackCards": normalize_tech_stack_cards(tech_stack_plan.get("techStackCards"), allowed_source_names),
        "skillKeywordGroups": normalize_skill_keyword_groups(tech_stack_plan.get("skillKeywordGroups")),
        "techStackSynthesis": normalize_string_list(tech_stack_plan.get("techStackSynthesis"), 6, 180),
    }


def normalize_tech_stack_cards(tech_stack_cards, allowed_source_names=None):
    if not isinstance(tech_stack_cards, list):
        return []

    normalized_tech_stack_cards = []

    for tech_stack_card in tech_stack_cards[:4]:
        if not isinstance(tech_stack_card, dict):
            continue

        title = str(tech_stack_card.get("title") or "").strip()
        description = str(tech_stack_card.get("description") or "").strip()

        if not title or not description:
            continue

        normalized_tech_stack_cards.append({
            "title": title[:80],
            "description": description[:380],
            "evidence": ", ".join(normalize_markdown_evidence(tech_stack_card.get("evidence"), allowed_source_names, 3)),
        })

    return normalized_tech_stack_cards


def normalize_skill_keyword_groups(skill_keyword_groups):
    if not isinstance(skill_keyword_groups, list):
        return []

    normalized_skill_keyword_groups = []

    for skill_keyword_group in skill_keyword_groups[:4]:
        if not isinstance(skill_keyword_group, dict):
            continue

        category = str(skill_keyword_group.get("category") or "").strip()
        keywords = normalize_skill_keywords(skill_keyword_group.get("keywords"))

        if not category or not keywords:
            continue

        normalized_skill_keyword_groups.append({
            "category": category[:40],
            "keywords": keywords,
        })

    return normalized_skill_keyword_groups


def normalize_skill_keywords(skill_keywords):
    if not isinstance(skill_keywords, list):
        return []

    normalized_skill_keywords = []
    allowed_tones = {"blue", "green", "amber", "coral"}
    allowed_strengths = {"strong", "medium", "weak"}

    for skill_keyword in skill_keywords:
        if not isinstance(skill_keyword, dict):
            continue

        label = str(skill_keyword.get("label") or "").strip()

        if not label:
            continue

        tone = str(skill_keyword.get("tone") or "").strip()
        strength = str(skill_keyword.get("strength") or "").strip()

        normalized_skill_keywords.append({
            "label": label[:32],
            "tone": tone if tone in allowed_tones else "blue",
            "strength": strength if strength in allowed_strengths else "medium",
            "weight": clamp_keyword_weight(skill_keyword.get("weight")),
        })

    normalized_skill_keywords.sort(key=lambda keyword: keyword["weight"], reverse=True)
    return normalized_skill_keywords


def clamp_keyword_weight(weight):
    try:
        keyword_weight = int(weight)
    except (TypeError, ValueError):
        keyword_weight = 60

    return max(0, min(100, keyword_weight))
