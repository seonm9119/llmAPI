OPENAI_GENERATED_PROVIDER = "openai-generated"
REPORT_CACHE_VERSION = "resume-report-openai-cache-v1"

REPORT_SECTION_NAMES = ["summary", "capabilities", "radar", "skills", "domains", "skillKeywords", "sources"]
RADAR_LABELS = ["PoC", "문제해결", "모델이해", "코딩", "서비스화", "문서화"]
SKILL_KEYWORD_GROUP_LABELS = ["AI 모델·학습", "문서 AI·OCR", "비전·의료영상", "서비스·인프라"]

RESUME_EVALUATION_FRAME = {
    "overallJudgement": "AI 결과를 실제 업무에서 검토하고 재사용할 수 있는 기준, 비교 지표, API, 화면으로 연결하는 Applied AI 엔지니어로 평가한다.",
    "sectionOrder": [
        "핵심 판정 4개를 먼저 선택한다.",
        "그 판정 축을 기준으로 AI 분야 Top 3를 선정한다.",
        "기술스택은 단순 나열이 아니라 앞선 판정과 분야를 증명하는 근거로 묶는다.",
        "총평은 세 섹션의 상위 abstraction으로 작성한다.",
    ],
    "strongSignals": [
        "Document AI/OCR에서는 문서 분류, 구조화, 위조검증, 보고서 자동화가 하나의 업무 흐름으로 반복된다.",
        "의료영상과 컴퓨터비전에서는 baseline, 개선 모델, 지표, 실패/한계 해석까지 같이 다루는 평가 태도가 보인다.",
        "FastAPI, React, Docker 기반으로 모델 산출물을 검토 가능한 데모와 서비스형 PoC로 전환하는 패턴이 반복된다.",
        "강점은 단일 모델 성능 주장이 아니라 데이터 품질, 검증 기준, 비교 지표, 사람의 리뷰 가능성을 함께 설계하는 작업 방식이다.",
    ],
}


def build_report_generation_payload(resume_report_context, report_prompt_version, evaluation_plan):
    return {
        "task": "Generate the resume page AI capability report from all project markdown evidence.",
        "promptVersion": report_prompt_version,
        "projectIndexSource": resume_report_context["projectIndexSource"],
        "projects": resume_report_context["projects"],
        "projectDetailSourceIndex": resume_report_context["projectDetailSourceIndex"],
        "projectEvidenceBriefs": resume_report_context["projectEvidenceBriefs"],
        "evidenceLedger": resume_report_context["evidenceLedger"],
        "evaluationPlan": evaluation_plan,
        "evaluationFrame": RESUME_EVALUATION_FRAME,
        "sourcePolicy": build_source_policy(resume_report_context),
        "outputGuidance": build_output_guidance(),
    }


def build_source_policy(resume_report_context):
    return {
        "mode": "server_managed_all_project_markdown_evidence_briefs",
        "indexSourceName": resume_report_context["projectIndexSource"]["name"],
        "projectCount": len(resume_report_context["projects"]),
        "detailSourceCount": len(resume_report_context["projectDetailSources"]),
        "briefCount": len(resume_report_context["projectEvidenceBriefs"]),
        "ledgerMarkdownCount": resume_report_context["evidenceLedger"]["sourcePolicy"]["ledgerMarkdownCount"],
    }


def build_output_guidance():
    return {
        "capabilities": "Choose four dynamic judgement axes from the full markdown evidence.",
        "radarLabels": RADAR_LABELS,
        "skillCards": "Use this section as technology-stack proof cards, not generic personal strengths.",
        "skillKeywordGroups": SKILL_KEYWORD_GROUP_LABELS,
        "skillKeywordWeights": "Use 0-100 weights. strong means 80-100, medium means 50-79, weak means 1-49.",
        "domainTop3": "Choose the Top 3 AI domains from the full evidence and explain problem-solving approach, evaluator judgement, and expansion potential.",
        "evidenceLabels": "Every evidence field must contain only bare markdown filenames ending in .md.",
        "titleStyle": "The title should be hiring-level and should not contain LLM 초안, Projection, gate, 사전집, 라벨, key, or signal.",
        "visibleProse": "Keep visible prose interviewer-facing. Avoid source-reading meta phrases, the wording 이 사람, and low-level implementation jargon when a hiring-level phrase is enough.",
        "qualityTarget": "The output should read like a strong GPT hiring evaluator wrote it after reading every project markdown file.",
    }
