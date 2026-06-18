import re
from pathlib import Path


PROJECT_HEADING_PATTERN = re.compile(r"^\s*###\s+(.+?)\s*$")
PROJECT_FIELD_PATTERN = re.compile(r"^\s*(?:-\s*)?([A-Za-z][A-Za-z0-9 /_-]*?)\s*:\s*(.*?)\s*$")
MARKDOWN_TITLE_PATTERN = re.compile(r"^\s*#\s+(.+?)\s*$")
MARKDOWN_SECTION_PATTERN = re.compile(r"^\s*#{2,3}\s+(.+?)\s*$")
MAX_EVIDENCE_BRIEF_CHARS = 4500
MAX_EVIDENCE_BRIEF_LINES = 70

EVIDENCE_BRIEF_SECTION_KEYWORDS = [
    "project report",
    "project position",
    "engineering competency",
    "practical skill",
    "benchmark summary",
    "result interpretation",
    "conclusion",
    "inference and service flow",
]

EVIDENCE_BRIEF_LINE_KEYWORDS = [
    "핵심",
    "목표",
    "역량",
    "평가",
    "결과",
    "해석",
    "지표",
    "비교",
    "서비스",
    "데모",
    "검증",
    "의료",
    "문서",
    "OCR",
    "LLM",
    "API",
    "FastAPI",
    "React",
    "Docker",
    "metric",
    "Metric",
    "benchmark",
    "Benchmark",
    "recruiter",
    "Recruiter",
]

LEDGER_SIGNAL_GROUPS = {
    "documentAi": {
        "label": "문서 AI/OCR",
        "keywords": [
            "document ai", "document_", "structured ocr", "deepseek-ocr", "paddleocr",
            "doclayout", "key-value", "key value", "tf-idf", "위조검증", "위조",
            "ocr", "mrv",
        ],
    },
    "medicalVision": {
        "label": "의료·비전 모델 평가",
        "keywords": [
            "medical", "mri", "brain", "pathology", "segmentation", "reconstruction",
            "computer vision", "ceramic", "opencv", "의료영상", "의료", "분할",
            "재구성", "병리", "영상의 특징점",
        ],
    },
    "servicePoC": {
        "label": "서비스형 PoC",
        "keywords": [
            "FastAPI", "React", "Docker", "Docker Compose", "API", "frontend", "프론트",
            "데모", "서비스", "ASP.NET", "Nginx", "container",
        ],
    },
    "evaluation": {
        "label": "평가·검증",
        "keywords": [
            "baseline", "benchmark", "metric", "Dice", "HD95", "PSNR", "SSIM",
            "Sensitivity", "mIoU", "평가", "검증", "비교", "해석", "지표",
        ],
    },
    "operationLimit": {
        "label": "검증 필요 지점",
        "keywords": [
            "limitation", "limit", "SLA", "clinical", "regulation", "production",
            "운영", "임상", "규제", "상용", "트래픽", "모니터링", "한계",
        ],
    },
}

LEDGER_TECH_STACK_GROUPS = {
    "AI 모델·학습": [
        "PyTorch", "MONAI", "Transformers", "PEFT", "LoRA", "QLoRA", "CLIP", "ResNet",
        "LSTM", "U-Net", "SwinUNETR", "Mamba", "GAN", "SSL", "SentenceTransformers",
    ],
    "문서 AI·OCR": [
        "OCR", "PaddleOCR", "DeepSeek-OCR", "DeepSeek-VL2", "DocLayout-YOLO", "TF-IDF",
        "layout", "key-value", "Document AI", "VLM", "LLM",
    ],
    "비전·의료영상": [
        "OpenCV", "Dice", "HD95", "PSNR", "SSIM", "Sensitivity", "NIfTI", "NiiVue",
        "nibabel", "mIoU", "MRI", "segmentation", "reconstruction",
    ],
    "서비스·인프라": [
        "FastAPI", "React", "Docker", "Docker Compose", "ASP.NET Core", "Kafka",
        "PostgreSQL", "MinIO", "Kubernetes", "AWS", "Nginx", "CUDA", "GPU",
    ],
}

PROJECT_FIELD_NAMES = {
    "period": "period",
    "source slides": "sourceSlides",
    "project position": "projectPosition",
    "methods": "methods",
    "languages": "languages",
    "apis / frameworks": "apisFrameworks",
    "cloud / deployment": "cloudDeployment",
    "libraries": "libraries",
    "feature pipeline": "featurePipeline",
    "evaluation": "evaluation",
    "metrics": "metrics",
    "key result": "keyResult",
    "best-fit use cases": "bestFitUseCases",
    "primary gpt reference file": "primaryGptReferenceFile",
    "reference rule": "referenceRule",
    "recruiter signal": "recruiterSignal",
}


def build_resume_report_context(index_file_path, source_alias_root_path=""):
    project_index_path = Path(index_file_path).resolve()
    source_root_path = project_index_path.parent
    project_index_source = read_markdown_source(project_index_path, project_index_path.name)
    project_sections = parse_project_sections(project_index_source["content"])
    projects = build_project_metadata_items(project_sections, source_root_path, source_alias_root_path)
    project_detail_sources = read_project_detail_markdown_sources(source_root_path, project_index_path)
    project_evidence_briefs = build_project_evidence_briefs(project_detail_sources)
    evidence_ledger = build_evidence_ledger(project_index_source, projects, project_detail_sources, project_evidence_briefs)

    return {
        "projectIndexSource": project_index_source,
        "projects": projects,
        "projectDetailSources": project_detail_sources,
        "projectDetailSourceIndex": build_project_detail_source_index(project_detail_sources),
        "projectEvidenceBriefs": project_evidence_briefs,
        "evidenceLedger": evidence_ledger,
    }


def build_resume_overall_context(index_file_path, source_alias_root_path=""):
    return build_resume_report_context(index_file_path, source_alias_root_path)


def read_markdown_source(markdown_file_path, source_name):
    try:
        markdown_content = Path(markdown_file_path).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise ValueError(f"{source_name} is not available.")
    except IsADirectoryError:
        raise ValueError(f"{source_name} is a directory, not a markdown file.")
    except UnicodeDecodeError:
        raise ValueError(f"{source_name} must be UTF-8 markdown text.")
    except OSError as file_error:
        raise ValueError(f"failed to read {source_name}: {file_error.strerror or file_error}")

    if not markdown_content:
        raise ValueError(f"{source_name} is empty.")

    return {
        "name": source_name,
        "content": markdown_content,
        "truncated": False,
    }


def parse_project_sections(markdown_content):
    project_sections = []
    current_project_section = None

    for markdown_line in markdown_content.splitlines():
        heading_match = PROJECT_HEADING_PATTERN.match(markdown_line)

        if heading_match:
            if current_project_section:
                project_sections.append(current_project_section)

            current_project_section = {
                "title": heading_match.group(1).strip(),
                "lines": [],
            }
            continue

        if current_project_section:
            current_project_section["lines"].append(markdown_line)

    if current_project_section:
        project_sections.append(current_project_section)

    return project_sections


def build_structured_projects(project_sections, source_root_path, source_alias_root_path=""):
    if not project_sections:
        raise ValueError("project index markdown must include at least one ### project heading.")

    projects = []

    for project_section in project_sections:
        project_fields = parse_project_fields(project_section["lines"])
        primary_reference_path = extract_primary_reference_path(project_fields.get("primaryGptReferenceFile", ""))
        detail_source_name = ""
        detail_content = ""

        if primary_reference_path:
            detail_file_path = resolve_markdown_file_path(primary_reference_path, source_root_path, source_alias_root_path)
            detail_source_name = build_markdown_source_name(detail_file_path, source_root_path)
            detail_source = read_markdown_source(detail_file_path, detail_source_name)
            detail_content = detail_source["content"]

        project_fields.pop("primaryGptReferenceFile", None)

        projects.append({
            "title": project_section["title"],
            "fields": project_fields,
            "primaryGptReferenceFile": detail_source_name,
            "primaryGptReferenceContent": detail_content,
        })

    return projects


def build_project_metadata_items(project_sections, source_root_path, source_alias_root_path=""):
    if not project_sections:
        raise ValueError("project index markdown must include at least one ### project heading.")

    projects = []

    for project_section in project_sections:
        project_fields = parse_project_fields(project_section["lines"])
        primary_reference_path = extract_primary_reference_path(project_fields.get("primaryGptReferenceFile", ""))
        primary_reference_source_name = ""

        if primary_reference_path:
            detail_file_path = resolve_markdown_file_path(primary_reference_path, source_root_path, source_alias_root_path)
            primary_reference_source_name = build_markdown_source_name(detail_file_path, source_root_path)

        project_fields.pop("primaryGptReferenceFile", None)

        projects.append({
            "title": project_section["title"],
            "fields": project_fields,
            "primaryGptReferenceFile": primary_reference_source_name,
        })

    return projects


def read_project_detail_markdown_sources(source_root_path, project_index_path):
    source_root_path = Path(source_root_path).resolve()
    project_index_path = Path(project_index_path).resolve()
    detail_sources = []

    for markdown_file_path in sorted(source_root_path.glob("*.md")):
        markdown_file_path = markdown_file_path.resolve()

        if markdown_file_path == project_index_path:
            continue

        source_name = build_markdown_source_name(markdown_file_path, source_root_path)
        detail_sources.append(read_markdown_source(markdown_file_path, source_name))

    return detail_sources


def build_project_detail_source_index(project_detail_sources):
    detail_source_index = []

    for project_detail_source in project_detail_sources:
        content = project_detail_source.get("content") or ""
        detail_source_index.append({
            "name": project_detail_source["name"],
            "charCount": len(content),
            "truncated": project_detail_source.get("truncated") is True,
        })

    return detail_source_index


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
        "purpose": "section planners use this ledger before writing resume-page judgements",
        "sourcePolicy": {
            "indexSourceName": project_index_source.get("name") or "projects.md",
            "projectCountFromIndex": len(projects),
            "detailMarkdownCount": len(project_detail_sources),
            "ledgerMarkdownCount": len(project_ledgers),
            "briefCount": len(project_evidence_briefs),
        },
        "projectLedgers": project_ledgers,
        "signalSummary": build_ledger_signal_summary(project_ledgers),
        "techStackSummary": build_ledger_tech_stack_summary(project_ledgers),
        "evaluationSummary": build_ledger_group_summary(project_ledgers, "evaluation"),
        "serviceSummary": build_ledger_group_summary(project_ledgers, "servicePoC"),
        "verificationLimitSummary": build_ledger_group_summary(project_ledgers, "operationLimit"),
    }


def build_index_project_ledger(project_index_source):
    source_name = project_index_source.get("name") or "projects.md"
    markdown_content = project_index_source.get("content") or ""
    evidence_brief_text = build_project_evidence_brief(markdown_content)

    return {
        "name": source_name,
        "title": extract_markdown_title(markdown_content, source_name),
        "signalGroups": find_ledger_signal_groups("\n".join([source_name, evidence_brief_text, markdown_content])),
        "techStacks": find_ledger_tech_stacks("\n".join([source_name, evidence_brief_text, markdown_content])),
        "representativeLines": build_ledger_representative_lines(evidence_brief_text),
    }


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
        combined_text = "\n".join([source_name, evidence_brief.get("title") or "", evidence_brief_text, markdown_content])

        project_ledgers.append({
            "name": source_name,
            "title": evidence_brief.get("title") or extract_markdown_title(markdown_content, source_name),
            "signalGroups": find_ledger_signal_groups(combined_text),
            "techStacks": find_ledger_tech_stacks(combined_text),
            "representativeLines": build_ledger_representative_lines(evidence_brief_text),
        })

    return project_ledgers


def find_ledger_signal_groups(text):
    signal_groups = []

    for signal_key, signal_config in LEDGER_SIGNAL_GROUPS.items():
        if contains_any_keyword(text, signal_config["keywords"]):
            signal_groups.append({
                "key": signal_key,
                "label": signal_config["label"],
            })

    return signal_groups


def find_ledger_tech_stacks(text):
    tech_stacks = []

    for category, stack_names in LEDGER_TECH_STACK_GROUPS.items():
        matched_stack_names = []

        for stack_name in stack_names:
            if contains_stack_name(text, stack_name) and stack_name not in matched_stack_names:
                matched_stack_names.append(stack_name)

        if matched_stack_names:
            tech_stacks.append({
                "category": category,
                "items": matched_stack_names,
            })

    return tech_stacks


def contains_stack_name(text, stack_name):
    text_lower = text.lower()
    stack_name_lower = stack_name.lower()

    return stack_name_lower in text_lower


def build_ledger_representative_lines(evidence_brief_text):
    representative_lines = []

    for evidence_line in evidence_brief_text.splitlines():
        cleaned_line = evidence_line.strip()

        if not cleaned_line:
            continue

        if contains_any_keyword(cleaned_line, EVIDENCE_BRIEF_LINE_KEYWORDS):
            representative_lines.append(cleaned_line[:260])

        if len(representative_lines) >= 8:
            break

    return representative_lines


def build_ledger_signal_summary(project_ledgers):
    signal_summary = []

    for signal_key, signal_config in LEDGER_SIGNAL_GROUPS.items():
        group_summary = build_ledger_group_summary(project_ledgers, signal_key)

        if group_summary["sourceCount"] == 0:
            continue

        group_summary["label"] = signal_config["label"]
        signal_summary.append(group_summary)

    signal_summary.sort(key=lambda group_summary: group_summary["sourceCount"], reverse=True)
    return signal_summary


def build_ledger_group_summary(project_ledgers, signal_key):
    source_names = []
    representative_lines = []

    for project_ledger in project_ledgers:
        if not project_has_signal(project_ledger, signal_key):
            continue

        source_name = project_ledger.get("name") or ""

        if source_name and source_name not in source_names:
            source_names.append(source_name)

        for representative_line in project_ledger.get("representativeLines") or []:
            if representative_line not in representative_lines:
                representative_lines.append(representative_line)

            if len(representative_lines) >= 8:
                break

    return {
        "key": signal_key,
        "sourceCount": len(source_names),
        "sources": source_names[:8],
        "representativeLines": representative_lines[:8],
    }


def project_has_signal(project_ledger, signal_key):
    for signal_group in project_ledger.get("signalGroups") or []:
        if signal_group.get("key") == signal_key:
            return True

    return False


def build_ledger_tech_stack_summary(project_ledgers):
    tech_stack_summary = []

    for category in LEDGER_TECH_STACK_GROUPS:
        stack_source_map = {}

        for project_ledger in project_ledgers:
            for tech_stack_group in project_ledger.get("techStacks") or []:
                if tech_stack_group.get("category") != category:
                    continue

                for stack_name in tech_stack_group.get("items") or []:
                    stack_source_map.setdefault(stack_name, [])

                    if project_ledger.get("name") not in stack_source_map[stack_name]:
                        stack_source_map[stack_name].append(project_ledger.get("name"))

        keywords = [
            {
                "label": stack_name,
                "sourceCount": len(source_names),
                "sources": source_names[:5],
            }
            for stack_name, source_names in stack_source_map.items()
        ]
        keywords.sort(key=lambda keyword: keyword["sourceCount"], reverse=True)

        tech_stack_summary.append({
            "category": category,
            "keywords": keywords,
        })

    return tech_stack_summary


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

    evidence_brief = "\n".join(selected_lines)

    if len(evidence_brief) > MAX_EVIDENCE_BRIEF_CHARS:
        return evidence_brief[:MAX_EVIDENCE_BRIEF_CHARS].rstrip()

    return evidence_brief


def append_evidence_brief_line(selected_lines, markdown_line):
    if markdown_line in selected_lines:
        return

    selected_lines.append(markdown_line)


def contains_any_keyword(text, keywords):
    text_lower = str(text or "").lower()
    return any(str(keyword or "").lower() in text_lower for keyword in keywords)


def parse_project_fields(markdown_lines):
    project_fields = {}
    current_field_name = ""

    for markdown_line in markdown_lines:
        field_match = PROJECT_FIELD_PATTERN.match(markdown_line)

        if field_match:
            current_field_name = normalize_project_field_name(field_match.group(1))
            project_fields[current_field_name] = clean_project_field_value(field_match.group(2))
            continue

        if not current_field_name or not markdown_line.strip():
            continue

        field_value = clean_project_field_value(markdown_line)

        if field_value:
            project_fields[current_field_name] = append_project_field_value(project_fields[current_field_name], field_value)

    return project_fields


def normalize_project_field_name(field_name):
    normalized_field_name = field_name.strip().lower()

    if normalized_field_name in PROJECT_FIELD_NAMES:
        return PROJECT_FIELD_NAMES[normalized_field_name]

    return build_camel_case_field_name(normalized_field_name)


def build_camel_case_field_name(field_name):
    field_name_parts = [field_name_part for field_name_part in re.split(r"[^a-z0-9]+", field_name) if field_name_part]

    if not field_name_parts:
        return "field"

    return field_name_parts[0] + "".join(field_name_part.title() for field_name_part in field_name_parts[1:])


def clean_project_field_value(field_value):
    cleaned_field_value = str(field_value or "").strip()

    if cleaned_field_value.startswith("-"):
        cleaned_field_value = cleaned_field_value[1:].strip()

    return cleaned_field_value


def append_project_field_value(current_field_value, field_value):
    if current_field_value:
        return f"{current_field_value}\n{field_value}"

    return field_value


def extract_primary_reference_path(primary_reference_value):
    for reference_line in str(primary_reference_value or "").splitlines():
        reference_path = clean_markdown_reference_path(reference_line)

        if is_markdown_reference_path(reference_path):
            return reference_path

    reference_path = clean_markdown_reference_path(primary_reference_value)

    if is_markdown_reference_path(reference_path):
        return reference_path

    return ""


def clean_markdown_reference_path(reference_text):
    reference_path = str(reference_text or "").strip()

    if not reference_path:
        return ""

    if reference_path.startswith("-"):
        reference_path = reference_path[1:].strip()

    markdown_link_match = re.search(r"\]\(([^)]+)\)", reference_path)

    if markdown_link_match:
        reference_path = markdown_link_match.group(1).strip()

    reference_path = reference_path.strip("`\"'<>")
    reference_path = reference_path.split("#", 1)[0].strip()

    return reference_path


def is_markdown_reference_path(reference_path):
    return bool(reference_path) and Path(reference_path).suffix.lower() == ".md"


def resolve_markdown_file_path(reference_path, source_root_path, source_alias_root_path=""):
    source_root_path = Path(source_root_path).resolve()
    reference_file_path = Path(reference_path)

    if reference_file_path.suffix.lower() != ".md":
        raise ValueError(f"{reference_path} is not a markdown file.")

    matching_file_path = find_markdown_file_by_name(reference_file_path.name, source_root_path)

    if matching_file_path:
        return matching_file_path

    raise ValueError(f"{reference_file_path.name} is not available under the resume archive projects folder.")


def find_markdown_file_by_name(file_name, source_root_path):
    if not file_name:
        return None

    matching_file_paths = sorted(
        file_path.resolve()
        for file_path in Path(source_root_path).resolve().rglob(file_name)
        if file_path.is_file() and file_path.suffix.lower() == ".md"
    )

    if not matching_file_paths:
        return None

    if len(matching_file_paths) > 1:
        relative_matches = ", ".join(
            file_path.relative_to(Path(source_root_path).resolve()).as_posix()
            for file_path in matching_file_paths
        )
        raise ValueError(f"{file_name} is ambiguous under the resume archive: {relative_matches}")

    return matching_file_paths[0]


def build_markdown_source_name(markdown_file_path, source_root_path):
    return Path(markdown_file_path).resolve().relative_to(Path(source_root_path).resolve()).as_posix()
