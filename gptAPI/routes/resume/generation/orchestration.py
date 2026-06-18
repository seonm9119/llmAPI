from .strategy import OPENAI_GENERATED_PROVIDER
from .tool_calling import (
    call_report_editor_tool,
    call_report_writer_tool,
    collect_allowed_source_names_tool,
    normalize_report_tool,
    plan_report_sections_tool,
)
from ..storage.cache import write_report_cache


def generate_and_cache_resume_report(
    resume_report_context,
    cache_key,
    model,
    create_structured_response,
    report_system_prompt,
    report_response_schema,
    report_prompt_version,
):
    allowed_source_names = collect_allowed_source_names_tool(resume_report_context)
    evaluation_plan = plan_report_sections_tool(resume_report_context, model)
    writer_output = call_report_writer_tool(
        create_structured_response,
        report_system_prompt,
        report_response_schema,
        resume_report_context,
        report_prompt_version,
        evaluation_plan,
        model,
    )
    editor_output = call_report_editor_tool(
        create_structured_response,
        report_response_schema,
        resume_report_context,
        report_prompt_version,
        evaluation_plan,
        writer_output["report"],
        model,
    )
    normalized_report = normalize_report_tool(editor_output["report"], allowed_source_names)
    cache_payload = write_report_cache(
        cache_key,
        OPENAI_GENERATED_PROVIDER,
        model,
        normalized_report,
    )

    return build_generation_result(cache_payload, evaluation_plan)


def build_generation_result(cache_payload, evaluation_plan):
    return {
        "provider": cache_payload["provider"],
        "model": cache_payload["model"],
        "cacheStatus": "stored",
        "generatedAt": cache_payload["generatedAt"],
        "evaluationPlan": evaluation_plan,
        "report": cache_payload["report"],
    }
