import re


MARKDOWN_SOURCE_PATTERN = re.compile(r"[^`\"'<>:;,\[\](){}\n]+?\.md")


def build_section_planner_payload(resume_report_context, task, prompt_version, extra_context=None):
    payload = {
        "task": task,
        "promptVersion": prompt_version,
        "projectIndexSource": resume_report_context["projectIndexSource"],
        "projects": resume_report_context["projects"],
        "projectDetailSourceIndex": resume_report_context["projectDetailSourceIndex"],
        "projectEvidenceBriefs": resume_report_context["projectEvidenceBriefs"],
        "evidenceLedger": resume_report_context.get("evidenceLedger", {}),
        "sourcePolicy": {
            "mode": "planner_reads_all_project_markdown_evidence_briefs",
            "indexSourceName": resume_report_context["projectIndexSource"]["name"],
            "projectCount": len(resume_report_context["projects"]),
            "detailSourceCount": len(resume_report_context["projectDetailSources"]),
            "briefCount": len(resume_report_context["projectEvidenceBriefs"]),
            "ledgerMarkdownCount": resume_report_context.get("evidenceLedger", {}).get("sourcePolicy", {}).get("ledgerMarkdownCount", 0),
        },
    }

    if isinstance(extra_context, dict):
        payload.update(extra_context)

    return payload


def collect_allowed_markdown_source_names(resume_report_context):
    source_names = []
    project_index_source = resume_report_context.get("projectIndexSource")

    if isinstance(project_index_source, dict):
        append_markdown_source_name(source_names, project_index_source.get("name"))

    project_detail_sources = resume_report_context.get("projectDetailSources")

    if isinstance(project_detail_sources, list):
        for project_detail_source in project_detail_sources:
            if isinstance(project_detail_source, dict):
                append_markdown_source_name(source_names, project_detail_source.get("name"))

    return source_names


def append_markdown_source_name(source_names, source_name):
    markdown_source_name = normalize_markdown_source_name(source_name)

    if markdown_source_name and markdown_source_name not in source_names:
        source_names.append(markdown_source_name)


def normalize_markdown_source_name(source_name):
    source_text = str(source_name or "").strip().strip("`\"'<>")

    if not source_text:
        return ""

    source_text = source_text.replace("\\", "/")
    lower_source_text = source_text.lower()
    markdown_extension_index = lower_source_text.find(".md")

    if markdown_extension_index < 0:
        return ""

    source_text = source_text[:markdown_extension_index + 3]

    if "/" in source_text:
        source_text = source_text.rsplit("/", 1)[-1]

    source_text = source_text.strip(" \t\r\n-•.,;:()[]{}'\"`")
    return source_text if source_text.lower().endswith(".md") else ""


def normalize_markdown_evidence(items, allowed_source_names=None, limit=3):
    if isinstance(items, list):
        evidence_items = items
    else:
        evidence_items = [items]

    allowed_markdown_source_names = [
        normalize_markdown_source_name(source_name)
        for source_name in (allowed_source_names or [])
    ]
    allowed_markdown_source_names = [
        source_name
        for source_name in allowed_markdown_source_names
        if source_name
    ]
    normalized_evidence = []

    for evidence_item in evidence_items:
        evidence_text = str(evidence_item or "").strip()

        if not evidence_text:
            continue

        for source_name in allowed_markdown_source_names:
            if source_name in evidence_text and source_name not in normalized_evidence:
                normalized_evidence.append(source_name)

        if allowed_markdown_source_names:
            continue

        for source_match in MARKDOWN_SOURCE_PATTERN.finditer(evidence_text):
            source_name = normalize_markdown_source_name(source_match.group(0))

            if source_name and source_name not in normalized_evidence:
                normalized_evidence.append(source_name)

    return normalized_evidence[:limit]


def normalize_string_list(items, limit, max_length):
    if not isinstance(items, list):
        return []

    normalized_items = []

    for item in items[:limit]:
        item_text = str(item or "").strip()

        if item_text and item_text not in normalized_items:
            normalized_items.append(item_text[:max_length])

    return normalized_items


def clamp_int(value, minimum, maximum, default_number):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default_number

    return max(minimum, min(maximum, number))
