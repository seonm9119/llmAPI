from .editor import REPORT_EDITOR_SYSTEM_PROMPT, build_report_editor_payload
from .strategy import build_report_generation_payload
from ..planner import create_resume_report_evaluation_plan
from ..processing.normalizer import normalize_markdown_source_name, normalize_openai_report


def collect_allowed_source_names_tool(resume_report_context):
    allowed_source_names = []
    project_index_source = resume_report_context.get("projectIndexSource")

    if isinstance(project_index_source, dict):
        append_allowed_source_name(allowed_source_names, project_index_source.get("name"))

    project_detail_sources = resume_report_context.get("projectDetailSources")

    if isinstance(project_detail_sources, list):
        for project_detail_source in project_detail_sources:
            if isinstance(project_detail_source, dict):
                append_allowed_source_name(allowed_source_names, project_detail_source.get("name"))

    return allowed_source_names


def plan_report_sections_tool(resume_report_context, model):
    return create_resume_report_evaluation_plan(resume_report_context, model)


def call_report_writer_tool(create_structured_response, system_prompt, response_schema, resume_report_context, report_prompt_version, evaluation_plan, model):
    writer_payload = build_report_generation_payload(resume_report_context, report_prompt_version, evaluation_plan)
    report_response, raw_response_text = create_structured_response(system_prompt, writer_payload, response_schema, model=model)

    return {
        "report": report_response,
        "rawResponseText": raw_response_text,
    }


def call_report_editor_tool(create_structured_response, response_schema, resume_report_context, report_prompt_version, evaluation_plan, draft_report, model):
    editor_payload = build_report_editor_payload(resume_report_context, report_prompt_version, evaluation_plan, draft_report)
    report_response, raw_response_text = create_structured_response(REPORT_EDITOR_SYSTEM_PROMPT, editor_payload, response_schema, model=model)

    return {
        "report": report_response,
        "rawResponseText": raw_response_text,
    }


def normalize_report_tool(report, allowed_source_names):
    return normalize_openai_report(report, allowed_source_names)


def append_allowed_source_name(allowed_source_names, source_name):
    markdown_source_name = normalize_markdown_source_name(source_name)

    if markdown_source_name and markdown_source_name not in allowed_source_names:
        allowed_source_names.append(markdown_source_name)
