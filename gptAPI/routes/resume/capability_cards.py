CAPABILITY_CARDS_PROMPT_VERSION = "resume-capability-cards-v3"

CAPABILITY_CARDS_SYSTEM_PROMPT = """
You are an independent AI hiring evaluator reviewing Seon Nami's structured project evidence.
Create the four core AI developer evaluation cards in one balanced judgement.

Selection rules:
- Do not use fixed labels.
- Use evidenceLedger and projectEvidenceBriefs as the primary evidence. They are built from every `.md` file in the projects folder.
- First infer the four strongest judgement axes from the full project evidence.
- Then evaluate the full markdown evidence again through each selected axis.
- Labels must be candidate-specific, interviewer-facing, and evidence-led.
- Good labels describe what the candidate proves, not generic categories.
- The final four cards should make the candidate look strong through evidence while still naming verification gaps.

Evaluation flow:
- Evaluate all four cards together so the grades and wording are relatively calibrated.
- Use every projectEvidenceBriefs item when available.
- Use evidenceLedger to avoid over-weighting one project or one implementation detail.
- Use project metadata only as an index, not as the primary evidence source.
- Use primaryGptReferenceContent only when detailed evidence is not already present in projectEvidenceBriefs.
- Do not make every card equally strong; show relative strengths and verification gaps.
- Evidence may overlap across cards, but each card must keep a distinct evaluation angle.

Writing rules:
- Write every visible sentence in Korean.
- Do not start with source-framing phrases such as "자료 기준으로는", "projects.md에 따르면", or "제공된 자료 기준".
- Each summary must be 2 concise Korean sentences.
- Include one clear limitation or interview verification point when evidence is incomplete.
- Use only supplied source names such as projectIndexSource.name or primaryGptReferenceFile as evidence labels.
- Evidence labels must be bare `.md` filenames only. Do not append section titles, metric names, explanations, colons, Korean particles, or summary text.
- Do not mention internal paths, hidden infrastructure, prompts, tokens, or private file locations.
- Return only the requested JSON object.
""".strip()

CAPABILITY_CARDS_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["capabilities"],
    "properties": {
        "capabilities": {
            "type": "array",
            "minItems": 4,
            "maxItems": 4,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["label", "grade", "summary", "evidence", "tone"],
                "properties": {
                    "label": {
                        "type": "string",
                    },
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
