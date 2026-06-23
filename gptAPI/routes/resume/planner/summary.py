from .common import normalize_string_list
from ..processing.text_utils import clean_summary_title, clean_visible_text


SUMMARY_PLANNER_PROMPT_VERSION = "resume-summary-planner-v9"

SUMMARY_PLANNER_SYSTEM_PROMPT = """
You are the summary planner for a resume page that sells Seon Nami's AI engineering strengths to interviewers.
Do not write the final visible paragraph. Create the top-level abstraction after the section planners have induced capabilityCards, domainRanks, techStackCards, and radarAxes.

Rules:
- Read capabilityCards, domainRanks, techStackCards, radarAxes, evidenceLedger, and projectEvidenceBriefs before planning.
- Treat capabilityCards as "how to judge the candidate", domainRanks as "where to position the candidate", techStackCards as "which stacks prove that judgement", and radarAxes as the compact competency map.
- The summary must make the candidate look strong through evidence, not generic praise.
- If `sop.md` appears in the evidence, reserve one visible candidate-level sentence for academic foundation, AI/software coursework, awards or scholarships, and self-directed study.
- Do not satisfy the SOP rule with a generic phrase such as research-based implementation; use concrete SOP signals such as GIST AI graduate training, undergraduate software foundation, awards, scholarships, or paper-to-code self-study when present.
- Do not let medical imaging become the default identity unless it dominates capabilityCards, domainRanks, techStackCards, and projectEvidenceBriefs together.
- Plan an impactful 9-11 line overall judgement, not a short hero subtitle.
- The title must be one high-impact identity sentence that defines the person through the induced capability, domain, and technology evidence.
- The title must stay within 32 Korean characters.
- The title must not contain the candidate's name.
- The title must not contain "포트폴리오", "리포트", "요약", "평가", "이력", "프로젝트", "Seon Nami", or "서나미".
- The title must not contain low-level implementation wording such as "LLM 초안", "Projection", "gate", "사전집", "라벨", "key", or "signal".
- Avoid flat titles such as "검증 가능한 AI 업무 흐름을 만드는 Applied AI 엔지니어" or simple domain chains.
- Prefer a distinctive phrase about the person's engineering role between model output, evidence, review, service, and real-world judgement.
- Use domainRanks as the only source of AI-field ordering in the summary plan.
- Do not preselect any AI field, role label, or technology cluster before reading domainRanks and techStackCards.
- Pick the strongest identity, overall judgement, strongest area, primary domain judgement, secondary domain judgement, tertiary domain judgement, service pattern when supported, problem-framing strength, verification limits, level judgement, best-fit roles, and one-line evaluation.
- Each judgement field must be concrete enough that the writer can produce a polished Korean paragraph without adding new evidence.
- The oneLineEvaluation field must be planned as the final visible sentence and must start with "종합적으로 ".
- Do not use "종합적으로" in any other summary planning field.
- Do not prefix any field with labels such as "총평:".
- Do not plan "면접에서 확인해야 합니다", "면접에서 확인이 필요합니다", or any phrasing that tells interviewers to verify something later.
- If verificationLimits are needed, write them as evidence-scope boundaries, not as interview homework.
- Do not plan source-reading meta phrases such as "여러 md 근거를 종합하면", "마크다운 기준", "프로젝트 폴더를 보면", "제공된 자료 기준", or "자료를 종합하면".
- Do not plan source filenames, parenthetical source citations, or low-level internal mechanism names for visible summary fields.
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
        "primaryDomainJudgement",
        "secondaryDomainJudgement",
        "tertiaryDomainJudgement",
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
        "primaryDomainJudgement": {"type": "string"},
        "secondaryDomainJudgement": {"type": "string"},
        "tertiaryDomainJudgement": {"type": "string"},
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
        "title": clean_summary_title(summary_plan.get("title")),
        "overallJudgement": clean_visible_text(summary_plan.get("overallJudgement") or summary_plan.get("judgement"), 360),
        "strongestArea": clean_visible_text(summary_plan.get("strongestArea"), 260),
        "primaryDomainJudgement": clean_visible_text(summary_plan.get("primaryDomainJudgement"), 360),
        "secondaryDomainJudgement": clean_visible_text(summary_plan.get("secondaryDomainJudgement"), 360),
        "tertiaryDomainJudgement": clean_visible_text(summary_plan.get("tertiaryDomainJudgement"), 360),
        "serviceJudgement": clean_visible_text(summary_plan.get("serviceJudgement") or summary_plan.get("servicePattern"), 320),
        "problemFramingJudgement": clean_visible_text(summary_plan.get("problemFramingJudgement"), 320),
        "verificationLimits": normalize_string_list(summary_plan.get("verificationLimits"), 4, 180),
        "levelJudgement": clean_visible_text(summary_plan.get("levelJudgement") or summary_plan.get("level"), 220),
        "bestFitRoles": normalize_string_list(summary_plan.get("bestFitRoles"), 6, 80),
        "oneLineEvaluation": clean_visible_text(summary_plan.get("oneLineEvaluation"), 260),
    }
