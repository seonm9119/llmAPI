OPENAI_GENERATED_PROVIDER = "openai-generated"
REPORT_CACHE_VERSION = "resume-report-openai-cache-v4"

REPORT_SECTION_NAMES = ["summary", "capabilities", "radar", "skills", "domains", "skillKeywords", "sources"]

RESUME_EVALUATION_FRAME = {
    "overallJudgement": "프로젝트 markdown 전체에서 반복되는 문제, 접근 방식, 평가 방식, 구현 산출물을 읽고 AI 세부 분야와 직무 역량 taxonomy를 OpenAI가 직접 귀납한다.",
    "sectionOrder": [
        "핵심 판정 4개를 근거에서 직접 이름 붙인다.",
        "그 판정 축과 전체 근거량을 기준으로 AI 분야 Top 3의 이름과 경계를 직접 만든다.",
        "기술스택은 고정 버킷이 아니라 앞선 판정과 분야를 증명하는 기술 클러스터로 묶는다.",
        "총평은 세 섹션의 상위 abstraction으로 작성한다.",
    ],
    "rankingPrinciples": [
        "AI 세부 분야는 프로젝트 수, 구현 깊이, 문제정의, 평가 방식, 서비스화 증거, 설명 가능성을 함께 보고 귀납한다.",
        "프롬프트의 예시나 서버의 키워드 버킷이 아니라 projectEvidenceBriefs의 실제 근거가 분야명과 순위를 결정해야 한다.",
        "상세 근거가 더 많고 문제해결·평가 깊이가 큰 분야가 제목과 총평에서 더 큰 비중을 가져야 한다.",
        "sop.md는 AI 세부 분야 카드가 아니라 학력, 이수 과목, 수상, 장학, 자기주도 학습을 증명하는 후보자 기반 근거로 총평과 역량 판정에 반영한다.",
        "의료영상 파일이 여러 개 있어도 파일 개수만으로 전체 정체성을 의료 중심으로 고정하지 않고 서비스화, 문서 OCR, 알고리즘 구현, 인프라 운영 근거와 함께 균형 있게 판단한다.",
        "직무 역량 축, 레이더 축, 기술 클러스터명도 고정 후보 없이 OpenAI가 직접 생성한다.",
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
        "capabilities": "Induce four judgement axes directly from the full markdown evidence. Keep each card title within 14 Korean characters.",
        "radarLabels": "Induce six radar labels from the same evidence and induced judgement axes. Do not use fixed labels.",
        "skillCards": "Use this section as technology-cluster proof cards, not generic personal strengths.",
        "skillKeywordGroups": "Induce technology keyword clusters from evidence. Category labels must be created by OpenAI, not chosen from a fixed list, and each category title must stay within 22 Korean characters.",
        "skillKeywordWeights": "Use 0-100 weights. strong means 80-100, medium means 50-79, weak means 1-49.",
        "domainTop3": "Induce the Top 3 AI/domain clusters from the full evidence and explain problem-solving approach, evaluator judgement, and expansion potential. Keep each domain card title within 22 Korean characters.",
        "evidenceLabels": "Every evidence field must contain only bare markdown filenames ending in .md.",
        "titleStyle": "The title should be hiring-level, no longer than 32 Korean characters, and should not contain LLM 초안, Projection, gate, 사전집, 라벨, key, or signal.",
        "summaryFinalSentence": "The summary description's final sentence must start with 종합적으로 and must be the only sentence using 종합적으로. It should compress level, strongest identity, and best-fit roles into one decisive hiring judgement.",
        "sopFoundation": "When sop.md is present, include one visible summary sentence with concrete academic and growth signals such as GIST AI graduate training, undergraduate software foundation, awards, scholarships, and self-directed paper-to-code study. Treat it as candidate-level proof, not an AI domain card.",
        "domainBalance": "Do not over-index on medical imaging only because several medical markdown files exist. Balance it with platform/service, document OCR, algorithmic CV/image processing, infrastructure operation, and SOP-backed growth evidence when supported.",
        "visibleProse": "Keep visible prose interviewer-facing. Avoid source-reading meta phrases, the wording 이 사람, and low-level implementation jargon when a hiring-level phrase is enough. Do not write 면접에서 확인해야 합니다, 면접에서 확인이 필요합니다, or any interviewer-homework phrasing.",
        "qualityTarget": "The output should read like a strong GPT hiring evaluator wrote it after reading every project markdown file, with domain emphasis proportional to evidence depth.",
    }
