from .tech_stack import (
    TECH_STACK_PLANNER_PROMPT_VERSION as SKILL_PLANNER_PROMPT_VERSION,
    TECH_STACK_PLANNER_RESPONSE_SCHEMA as SKILL_PLANNER_RESPONSE_SCHEMA,
    TECH_STACK_PLANNER_SYSTEM_PROMPT as SKILL_PLANNER_SYSTEM_PROMPT,
    normalize_tech_stack_cards,
    normalize_tech_stack_plan,
)


def normalize_skill_plan(skill_plan, allowed_source_names=None):
    normalized_tech_stack_plan = normalize_tech_stack_plan(skill_plan, allowed_source_names)
    return normalized_tech_stack_plan["techStackCards"]


__all__ = [
    "SKILL_PLANNER_PROMPT_VERSION",
    "SKILL_PLANNER_RESPONSE_SCHEMA",
    "SKILL_PLANNER_SYSTEM_PROMPT",
    "normalize_skill_plan",
    "normalize_tech_stack_cards",
    "normalize_tech_stack_plan",
]
