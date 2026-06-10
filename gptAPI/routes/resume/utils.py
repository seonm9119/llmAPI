import re
from pathlib import Path


PROJECT_HEADING_PATTERN = re.compile(r"^\s*###\s+(.+?)\s*$")
PROJECT_FIELD_PATTERN = re.compile(r"^\s*(?:-\s*)?([A-Za-z][A-Za-z0-9 /_-]*?)\s*:\s*(.*?)\s*$")

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
    source_root_path = Path(index_file_path).resolve().parent
    project_index_path = Path(index_file_path).resolve()
    project_index_source = read_markdown_source(project_index_path, project_index_path.name)
    project_sections = parse_project_sections(project_index_source["content"])
    projects = build_structured_projects(project_sections, source_root_path, source_alias_root_path)

    return {
        "projectIndexSource": project_index_source,
        "projects": projects,
    }


def build_resume_overall_context(index_file_path, source_alias_root_path=""):
    source_root_path = Path(index_file_path).resolve().parent
    project_index_path = Path(index_file_path).resolve()
    project_index_source = read_markdown_source(project_index_path, project_index_path.name)
    project_sections = parse_project_sections(project_index_source["content"])
    projects = build_project_metadata_items(project_sections, source_root_path, source_alias_root_path)

    return {
        "projectIndexSource": {
            "name": project_index_source["name"],
        },
        "projects": projects,
    }


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
    detail_file_path = Path(reference_path)

    if detail_file_path.is_absolute():
        detail_file_path = map_source_alias_path(detail_file_path, source_root_path, source_alias_root_path)
    else:
        detail_file_path = source_root_path / detail_file_path

    detail_file_path = detail_file_path.resolve()

    if detail_file_path.suffix.lower() != ".md":
        raise ValueError(f"{reference_path} is not a markdown file.")

    if not detail_file_path.is_relative_to(source_root_path):
        raise ValueError(f"{reference_path} is outside the resume report source root.")

    return detail_file_path


def map_source_alias_path(detail_file_path, source_root_path, source_alias_root_path):
    if not source_alias_root_path:
        return detail_file_path

    source_alias_root_path = Path(source_alias_root_path).resolve()

    try:
        detail_relative_path = detail_file_path.resolve().relative_to(source_alias_root_path)
    except ValueError:
        return detail_file_path

    return source_root_path / detail_relative_path


def build_markdown_source_name(markdown_file_path, source_root_path):
    return Path(markdown_file_path).resolve().relative_to(Path(source_root_path).resolve()).as_posix()
