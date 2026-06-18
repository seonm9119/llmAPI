import re


MARKDOWN_TITLE_PATTERN = re.compile(r"^\s*#\s+(.+?)\s*$")
MARKDOWN_SECTION_PATTERN = re.compile(r"^\s*#{2,3}\s+(.+?)\s*$")
TERM_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9.+#_-]{1,}|[가-힣]{2,}")
MAX_EVIDENCE_BRIEF_CHARS = 4500
MAX_EVIDENCE_BRIEF_LINES = 70
MAX_PROJECT_TERMS = 24
MAX_REPEATED_TERMS = 60

EVIDENCE_BRIEF_SECTION_KEYWORDS = [
    "project report",
    "project position",
    "engineering competency",
    "practical skill",
    "benchmark summary",
    "result interpretation",
    "conclusion",
    "method",
    "methods",
    "pipeline",
    "evaluation",
    "metrics",
    "key result",
    "recruiter signal",
    "implementation",
    "architecture",
    "dataset",
    "service flow",
]

EVIDENCE_BRIEF_LINE_KEYWORDS = [
    "핵심",
    "목표",
    "문제",
    "접근",
    "방법",
    "구현",
    "역량",
    "평가",
    "결과",
    "해석",
    "지표",
    "비교",
    "실험",
    "서비스",
    "데모",
    "검증",
    "모델",
    "학습",
    "데이터",
    "구조",
    "파이프라인",
    "한계",
    "role",
    "method",
    "evaluation",
    "metrics",
    "result",
    "benchmark",
    "recruiter",
    "api",
    "framework",
    "library",
]

TERM_STOPWORDS = {
    "project",
    "report",
    "position",
    "method",
    "methods",
    "evaluation",
    "metrics",
    "result",
    "summary",
    "source",
    "primary",
    "reference",
    "file",
    "based",
    "using",
    "with",
    "and",
    "the",
    "for",
    "from",
    "this",
    "that",
    "프로젝트",
    "기반",
    "결과",
    "평가",
    "구현",
    "사용",
    "통해",
    "대한",
    "위한",
    "중심",
    "역량",
    "핵심",
    "구조",
    "내용",
    "정리",
    "가능",
    "비교",
}


def build_project_evidence_briefs(project_detail_sources):
    evidence_briefs = []

    for project_detail_source in project_detail_sources:
        content = project_detail_source.get("content") or ""
        evidence_briefs.append({
            "name": project_detail_source["name"],
            "title": extract_markdown_title(content, project_detail_source["name"]),
            "brief": build_project_evidence_brief(content),
        })

    return evidence_briefs


def build_evidence_ledger(project_index_source, projects, project_detail_sources, project_evidence_briefs):
    project_ledgers = [build_index_project_ledger(project_index_source)] + build_project_ledgers(project_detail_sources, project_evidence_briefs)

    return {
        "purpose": "coverage ledger only; OpenAI must induce domains, competencies, and technology clusters from projectEvidenceBriefs",
        "sourcePolicy": {
            "indexSourceName": project_index_source.get("name") or "projects.md",
            "projectCountFromIndex": len(projects),
            "detailMarkdownCount": len(project_detail_sources),
            "ledgerMarkdownCount": len(project_ledgers),
            "briefCount": len(project_evidence_briefs),
        },
        "projectLedgers": project_ledgers,
        "repeatedTermSummary": build_repeated_term_summary(project_ledgers),
    }


def build_index_project_ledger(project_index_source):
    source_name = project_index_source.get("name") or "projects.md"
    markdown_content = project_index_source.get("content") or ""
    evidence_brief_text = build_project_evidence_brief(markdown_content)

    return build_project_ledger(source_name, markdown_content, evidence_brief_text)


def build_project_ledgers(project_detail_sources, project_evidence_briefs):
    evidence_brief_by_name = {
        project_evidence_brief["name"]: project_evidence_brief
        for project_evidence_brief in project_evidence_briefs
        if project_evidence_brief.get("name")
    }
    project_ledgers = []

    for project_detail_source in project_detail_sources:
        source_name = project_detail_source.get("name") or ""
        markdown_content = project_detail_source.get("content") or ""
        evidence_brief = evidence_brief_by_name.get(source_name, {})
        evidence_brief_text = evidence_brief.get("brief") or ""
        project_ledgers.append(build_project_ledger(source_name, markdown_content, evidence_brief_text))

    return project_ledgers


def build_project_ledger(source_name, markdown_content, evidence_brief_text):
    title = extract_markdown_title(markdown_content, source_name)
    representative_lines = build_representative_lines(evidence_brief_text)
    term_source_text = "\n".join([source_name, title, evidence_brief_text])

    return {
        "name": source_name,
        "title": title,
        "representativeLines": representative_lines,
        "sourceTerms": extract_key_terms(term_source_text, MAX_PROJECT_TERMS),
    }


def build_representative_lines(evidence_brief_text):
    representative_lines = []

    for evidence_line in evidence_brief_text.splitlines():
        cleaned_line = evidence_line.strip()

        if not cleaned_line:
            continue

        representative_lines.append(cleaned_line[:260])

        if len(representative_lines) >= 8:
            break

    return representative_lines


def build_repeated_term_summary(project_ledgers):
    repeated_terms_by_key = {}

    for project_ledger in project_ledgers:
        source_name = project_ledger.get("name") or ""

        for source_term in project_ledger.get("sourceTerms") or []:
            label = source_term.get("label") or ""
            term_key = label.lower()

            if not label:
                continue

            repeated_terms_by_key.setdefault(term_key, {
                "label": label,
                "sourceCount": 0,
                "sources": [],
            })

            if source_name and source_name not in repeated_terms_by_key[term_key]["sources"]:
                repeated_terms_by_key[term_key]["sources"].append(source_name)
                repeated_terms_by_key[term_key]["sourceCount"] += 1

    repeated_terms = list(repeated_terms_by_key.values())
    repeated_terms.sort(key=lambda term: (term["sourceCount"], len(term["label"])), reverse=True)
    return repeated_terms[:MAX_REPEATED_TERMS]


def extract_markdown_title(markdown_content, default_title):
    for markdown_line in markdown_content.splitlines():
        title_match = MARKDOWN_TITLE_PATTERN.match(markdown_line)

        if title_match:
            return title_match.group(1).strip()

    return default_title


def build_project_evidence_brief(markdown_content):
    selected_lines = []
    current_section_is_relevant = False

    for markdown_line in markdown_content.splitlines():
        cleaned_line = markdown_line.strip()

        if not cleaned_line:
            continue

        section_match = MARKDOWN_SECTION_PATTERN.match(cleaned_line)

        if section_match:
            section_title = section_match.group(1).strip()
            current_section_is_relevant = contains_any_keyword(section_title.lower(), EVIDENCE_BRIEF_SECTION_KEYWORDS)

            if current_section_is_relevant:
                append_evidence_brief_line(selected_lines, cleaned_line)

            continue

        if current_section_is_relevant or contains_any_keyword(cleaned_line, EVIDENCE_BRIEF_LINE_KEYWORDS):
            append_evidence_brief_line(selected_lines, cleaned_line)

        if len(selected_lines) >= MAX_EVIDENCE_BRIEF_LINES:
            break

    if not selected_lines:
        selected_lines = collect_initial_markdown_lines(markdown_content)

    evidence_brief = "\n".join(selected_lines)

    if len(evidence_brief) > MAX_EVIDENCE_BRIEF_CHARS:
        return evidence_brief[:MAX_EVIDENCE_BRIEF_CHARS].rstrip()

    return evidence_brief


def collect_initial_markdown_lines(markdown_content):
    selected_lines = []

    for markdown_line in markdown_content.splitlines():
        cleaned_line = markdown_line.strip()

        if not cleaned_line:
            continue

        append_evidence_brief_line(selected_lines, cleaned_line)

        if len(selected_lines) >= MAX_EVIDENCE_BRIEF_LINES:
            break

    return selected_lines


def append_evidence_brief_line(selected_lines, markdown_line):
    if markdown_line in selected_lines:
        return

    selected_lines.append(markdown_line)


def extract_key_terms(text, limit):
    terms_by_key = {}

    for term_match in TERM_PATTERN.finditer(str(text or "")):
        term = clean_term(term_match.group(0))

        if not should_keep_term(term):
            continue

        term_key = term.lower()

        if term_key not in terms_by_key:
            terms_by_key[term_key] = {
                "label": term,
                "count": 0,
            }

        terms_by_key[term_key]["count"] += 1

    terms = list(terms_by_key.values())
    terms.sort(key=lambda term: (term["count"], len(term["label"])), reverse=True)
    return terms[:limit]


def clean_term(term):
    return str(term or "").strip(" \t\r\n-•.,;:()[]{}'\"`")


def should_keep_term(term):
    if len(term) < 2:
        return False

    if term.lower() in TERM_STOPWORDS:
        return False

    if term.isdigit():
        return False

    return True


def contains_any_keyword(text, keywords):
    text_lower = str(text or "").lower()
    return any(str(keyword or "").lower() in text_lower for keyword in keywords)
