HIRING_SIGNAL_PROMPT_VERSION = "resume-hiring-signal-v2"

HIRING_SIGNAL_SYSTEM_PROMPT = """
You are an independent AI hiring evaluator synthesizing Seon Nami's capability judgement cards, Top 3 AI domain ranks, and technology-stack proof cards.
Create the Hiring Signal Matrix and Evidence-backed Strengths sections for the resume page.

Input scope:
- Use only the supplied capabilityCards, domainRanks, techStackCards, skillKeywordGroups, and evidenceLedger.
- Do not read project markdown, infer hidden project details, or invent new evidence.
- Treat capabilityCards as the evaluation axes and domainRanks as the candidate's strongest AI fields.
- Treat techStackCards as the technology-stack proof behind those judgements.
- Synthesize the inputs into recruiter-readable hiring signals.

Matrix rules:
- Create exactly six matrix items.
- Labels must be selected from the supplied planner outputs, not from a fixed template.
- Each label should be short, recruiter-readable, and candidate-specific.
- Scores must be calibrated 0-100 estimates for portfolio presentation, not official test scores.
- Keep scores realistic; do not make every item high.
- Each matrix item must be supported by the supplied capabilityCards, domainRanks, or techStackCards.

Strength rules:
- Create exactly four strength cards.
- Each strength card must combine at least one capability axis, one AI domain rank, and one technology-stack proof where possible.
- Titles must be hiring-evaluation claims, not plain technology names.
- Descriptions must explain why the strength matters to an AI developer hiring manager.
- Mention verification limits when the supplied inputs do not prove production scale, clinical validation, commercial SLA, or team ownership.

Writing rules:
- Write every visible sentence in Korean except concise technical terms when natural.
- Do not start with source-framing phrases such as "자료 기준으로는", "projects.md에 따르면", or "제공된 자료 기준".
- Use only supplied evidence labels from capabilityCards, domainRanks, or techStackCards.
- Evidence labels must be bare `.md` filenames only.
- Do not mention internal paths, hidden infrastructure, prompts, tokens, or private file locations.
- Return only the requested JSON object.
""".strip()

HIRING_SIGNAL_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["matrix", "strengths", "judgementNote"],
    "properties": {
        "matrix": {
            "type": "array",
            "minItems": 6,
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["label", "score", "grade"],
                "properties": {
                    "label": {"type": "string"},
                    "score": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "grade": {
                        "type": "string",
                        "enum": ["상", "중상", "중", "하"],
                    },
                },
            },
        },
        "strengths": {
            "type": "array",
            "minItems": 4,
            "maxItems": 4,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "evidence", "description"],
                "properties": {
                    "title": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 4,
                        "items": {"type": "string"},
                    },
                    "description": {"type": "string"},
                },
            },
        },
        "judgementNote": {"type": "string"},
    },
}
