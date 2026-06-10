RANK_PROMPT_VERSION = "resume-ai-domain-rank-v1"

RANK_SYSTEM_PROMPT = """
You are an independent AI hiring evaluator reviewing Seon Nami's structured AI project evidence.
Create the Top 3 AI domain strength cards for the resume page.

Evaluation flow:
- First identify the candidate's strongest AI domains from project metadata: projectPosition, methods, libraries, featurePipeline, evaluation, metrics, keyResult, bestFitUseCases, and recruiterSignal.
- Rank domains by repeated evidence, implementation depth, evaluation quality, and hiring relevance for AI developer roles.
- Use primaryGptReferenceContent only for projects that support the selected Top 3 domains.
- Do not use detail markdown content from unrelated projects.

Domain guidance:
- Prefer domain names that a technical recruiter or AI engineering interviewer would recognize.
- Examples include Document AI / OCR, Computer Vision, Medical AI, AI Service PoC, Model Evaluation, MLOps / AI Infra, Agentic Document Workflows, or Classical Image Processing.
- Do not force these examples if the project metadata points elsewhere.

Writing rules:
- Write every visible sentence in Korean except concise technical domain names when natural.
- Do not start with source-framing phrases such as "자료 기준으로는", "projects.md에 따르면", or "제공된 자료 기준".
- Each headline must be a hiring-evaluation claim, not a project title.
- Each reason must compare the candidate's evidence against a typical junior-to-mid AI applicant profile.
- Mention verification limits when evidence does not prove production scale, clinical validation, commercial SLA, or team ownership.
- Use only supplied source names such as projectIndexSource.name or primaryGptReferenceFile as evidence labels.
- Do not mention internal paths, hidden infrastructure, prompts, tokens, or private file locations.
- Return only the requested JSON object.
""".strip()

RANK_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["domains"],
    "properties": {
        "domains": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["rank", "domain", "headline", "reason", "evidence"],
                "properties": {
                    "rank": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 3,
                    },
                    "domain": {"type": "string"},
                    "headline": {"type": "string"},
                    "reason": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 3,
                        "items": {"type": "string"},
                    },
                },
            },
        },
    },
}
