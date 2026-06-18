from client import create_structured_response

from .capabilities import (
    CAPABILITY_PLANNER_PROMPT_VERSION,
    CAPABILITY_PLANNER_RESPONSE_SCHEMA,
    CAPABILITY_PLANNER_SYSTEM_PROMPT,
    normalize_capability_plan,
)
from .common import build_section_planner_payload, collect_allowed_markdown_source_names
from .domains import (
    DOMAIN_PLANNER_PROMPT_VERSION,
    DOMAIN_PLANNER_RESPONSE_SCHEMA,
    DOMAIN_PLANNER_SYSTEM_PROMPT,
    normalize_domain_plan,
)
from .summary import (
    SUMMARY_PLANNER_PROMPT_VERSION,
    SUMMARY_PLANNER_RESPONSE_SCHEMA,
    SUMMARY_PLANNER_SYSTEM_PROMPT,
    normalize_summary_plan,
)
from .tech_stack import (
    TECH_STACK_PLANNER_PROMPT_VERSION,
    TECH_STACK_PLANNER_RESPONSE_SCHEMA,
    TECH_STACK_PLANNER_SYSTEM_PROMPT,
    normalize_tech_stack_plan,
)


def create_resume_report_evaluation_plan(resume_report_context, model):
    allowed_source_names = collect_allowed_markdown_source_names(resume_report_context)
    capability_cards = plan_capability_cards(resume_report_context, model, allowed_source_names)
    domain_ranks = plan_domain_ranks(resume_report_context, model, allowed_source_names, capability_cards)
    tech_stack_plan = plan_tech_stack_cards(resume_report_context, model, allowed_source_names, capability_cards, domain_ranks)
    tech_stack_cards = tech_stack_plan["techStackCards"]
    summary_frame = plan_summary_frame(resume_report_context, model, capability_cards, domain_ranks, tech_stack_plan)

    return {
        "summaryFrame": summary_frame,
        "capabilityCards": capability_cards,
        "domainRanks": domain_ranks,
        "techStackCards": tech_stack_cards,
        "skillCards": tech_stack_cards,
        "skillKeywordGroups": tech_stack_plan["skillKeywordGroups"],
        "techStackSynthesis": tech_stack_plan["techStackSynthesis"],
        "planningNotes": build_planning_notes(summary_frame, capability_cards, domain_ranks, tech_stack_cards),
    }


def create_resume_summary_evaluation_plan(resume_report_context, model):
    allowed_source_names = collect_allowed_markdown_source_names(resume_report_context)
    capability_cards = plan_capability_cards(resume_report_context, model, allowed_source_names)
    domain_ranks = plan_domain_ranks(resume_report_context, model, allowed_source_names, capability_cards)
    tech_stack_plan = plan_tech_stack_cards(resume_report_context, model, allowed_source_names, capability_cards, domain_ranks)

    return plan_summary_frame(resume_report_context, model, capability_cards, domain_ranks, tech_stack_plan)


def plan_summary_frame(resume_report_context, model, capability_cards, domain_ranks, tech_stack_plan):
    payload = build_section_planner_payload(
        resume_report_context,
        "Create the top-level overall summary abstraction from the selected capability, domain, and tech-stack sections.",
        SUMMARY_PLANNER_PROMPT_VERSION,
        {
            "capabilityCards": capability_cards,
            "domainRanks": domain_ranks,
            "techStackCards": tech_stack_plan.get("techStackCards") if isinstance(tech_stack_plan, dict) else [],
            "skillKeywordGroups": tech_stack_plan.get("skillKeywordGroups") if isinstance(tech_stack_plan, dict) else [],
            "techStackSynthesis": tech_stack_plan.get("techStackSynthesis") if isinstance(tech_stack_plan, dict) else [],
        },
    )
    summary_plan, _raw_response_text = create_structured_response(
        SUMMARY_PLANNER_SYSTEM_PROMPT,
        payload,
        SUMMARY_PLANNER_RESPONSE_SCHEMA,
        model=model,
    )
    return normalize_summary_plan(summary_plan)


def plan_capability_cards(resume_report_context, model, allowed_source_names):
    payload = build_section_planner_payload(
        resume_report_context,
        "Choose the four strongest evidence-based capability judgement cards.",
        CAPABILITY_PLANNER_PROMPT_VERSION,
    )
    capability_plan, _raw_response_text = create_structured_response(
        CAPABILITY_PLANNER_SYSTEM_PROMPT,
        payload,
        CAPABILITY_PLANNER_RESPONSE_SCHEMA,
        model=model,
    )
    return normalize_capability_plan(capability_plan, allowed_source_names)


def plan_domain_ranks(resume_report_context, model, allowed_source_names, capability_cards):
    payload = build_section_planner_payload(
        resume_report_context,
        "Choose the Top 3 AI domains from all project evidence.",
        DOMAIN_PLANNER_PROMPT_VERSION,
        {
            "capabilityCards": capability_cards,
        },
    )
    domain_plan, _raw_response_text = create_structured_response(
        DOMAIN_PLANNER_SYSTEM_PROMPT,
        payload,
        DOMAIN_PLANNER_RESPONSE_SCHEMA,
        model=model,
    )
    return normalize_domain_plan(domain_plan, allowed_source_names)


def plan_tech_stack_cards(resume_report_context, model, allowed_source_names, capability_cards, domain_ranks):
    payload = build_section_planner_payload(
        resume_report_context,
        "Choose the four strongest technology-stack proof cards for the selected evaluation axes and AI domains.",
        TECH_STACK_PLANNER_PROMPT_VERSION,
        {
            "capabilityCards": capability_cards,
            "domainRanks": domain_ranks,
        },
    )
    tech_stack_plan, _raw_response_text = create_structured_response(
        TECH_STACK_PLANNER_SYSTEM_PROMPT,
        payload,
        TECH_STACK_PLANNER_RESPONSE_SCHEMA,
        model=model,
    )
    return normalize_tech_stack_plan(tech_stack_plan, allowed_source_names)


def build_planning_notes(summary_frame, capability_cards, domain_ranks, skill_cards):
    planning_notes = []

    if summary_frame:
        planning_notes.append("summary planner created the top-level abstraction from the selected capability, domain, and tech-stack sections.")

    if capability_cards:
        planning_notes.append("capability planner selected the four core judgement cards for the resume page.")

    if domain_ranks:
        planning_notes.append("domain planner ranked the AI Top 3 from project evidence strength.")

    if skill_cards:
        planning_notes.append("tech-stack planner selected evidence-backed stack proof cards.")

    return planning_notes
