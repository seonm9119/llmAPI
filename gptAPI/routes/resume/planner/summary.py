from .common import normalize_string_list


SUMMARY_PLANNER_PROMPT_VERSION = "resume-summary-planner-v4"

SUMMARY_PLANNER_SYSTEM_PROMPT = """
You are the summary planner for a resume page that sells Seon Nami's AI engineering strengths to interviewers.
Do not write the final visible paragraph. Create the top-level abstraction after the section planners have selected capabilityCards, domainRanks, and techStackCards.

Rules:
- Read capabilityCards, domainRanks, techStackCards, evidenceLedger, and projectEvidenceBriefs before planning.
- Treat capabilityCards as "how to judge the candidate", domainRanks as "where to position the candidate", and techStackCards as "which stacks prove that judgement".
- The summary must make the candidate look strong through evidence, not generic praise.
- Plan an impactful 9-11 line overall judgement, not a short hero subtitle.
- The title must be one high-impact identity sentence that defines the person through the selected capability, domain, and tech-stack evidence.
- The title must not contain the candidate's name.
- The title must not contain "포트폴리오", "리포트", "요약", "평가", "이력", "프로젝트", "Seon Nami", or "서나미".
- The title must not contain low-level implementation wording such as "LLM 초안", "Projection", "gate", "사전집", "라벨", "key", or "signal".
- Avoid flat titles such as "검증 가능한 AI 업무 흐름을 만드는 Applied AI 엔지니어" or simple domain chains.
- Prefer a distinctive phrase about the person's engineering role between model output, evidence, review, service, and real-world judgement.
- Pick the strongest identity, overall judgement, strongest area, Document AI/OCR evidence, medical/computer-vision evidence, service pattern, problem-framing strength, verification limits, level judgement, best-fit roles, and one-line evaluation.
- Each judgement field must be concrete enough that the writer can produce a polished Korean paragraph without adding new evidence.
- Do not prefix any field with labels such as "총평:".
- Do not plan source-reading meta phrases such as "여러 md 근거를 종합하면", "마크다운 기준", "프로젝트 폴더를 보면", "제공된 자료 기준", or "자료를 종합하면".
- Do not call the candidate "이 사람"; use "지원자" sparingly or write with the capability as the sentence subject.
- Do not call the candidate "시니어".
- Return only the requested JSON object.
""".strip()

SUMMARY_PLANNER_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title",
        "overallJudgement",
        "strongestArea",
        "documentAiJudgement",
        "medicalVisionJudgement",
        "serviceJudgement",
        "problemFramingJudgement",
        "verificationLimits",
        "levelJudgement",
        "bestFitRoles",
        "oneLineEvaluation",
    ],
    "properties": {
        "title": {"type": "string"},
        "overallJudgement": {"type": "string"},
        "strongestArea": {"type": "string"},
        "documentAiJudgement": {"type": "string"},
        "medicalVisionJudgement": {"type": "string"},
        "serviceJudgement": {"type": "string"},
        "problemFramingJudgement": {"type": "string"},
        "verificationLimits": {
            "type": "array",
            "minItems": 2,
            "maxItems": 4,
            "items": {"type": "string"},
        },
        "levelJudgement": {"type": "string"},
        "bestFitRoles": {
            "type": "array",
            "minItems": 4,
            "maxItems": 6,
            "items": {"type": "string"},
        },
        "oneLineEvaluation": {"type": "string"},
    },
}


def normalize_summary_plan(summary_plan):
    if not isinstance(summary_plan, dict):
        return {}

    return {
        "title": str(summary_plan.get("title") or "").strip()[:80],
        "overallJudgement": str(summary_plan.get("overallJudgement") or summary_plan.get("judgement") or "").strip()[:360],
        "strongestArea": str(summary_plan.get("strongestArea") or "").strip()[:260],
        "documentAiJudgement": str(summary_plan.get("documentAiJudgement") or "").strip()[:360],
        "medicalVisionJudgement": str(summary_plan.get("medicalVisionJudgement") or "").strip()[:360],
        "serviceJudgement": str(summary_plan.get("serviceJudgement") or summary_plan.get("servicePattern") or "").strip()[:320],
        "problemFramingJudgement": str(summary_plan.get("problemFramingJudgement") or "").strip()[:320],
        "verificationLimits": normalize_string_list(summary_plan.get("verificationLimits"), 4, 180),
        "levelJudgement": str(summary_plan.get("levelJudgement") or summary_plan.get("level") or "").strip()[:220],
        "bestFitRoles": normalize_string_list(summary_plan.get("bestFitRoles"), 6, 80),
        "oneLineEvaluation": str(summary_plan.get("oneLineEvaluation") or "").strip()[:260],
    }
