from .common import clamp_int
from ..processing.text_utils import clean_visible_text


RADAR_PLANNER_PROMPT_VERSION = "resume-radar-planner-v1"

RADAR_PLANNER_SYSTEM_PROMPT = """
You are the radar-axis planner for the resume page.
Induce six radar axes from project markdown evidence, capabilityCards, domainRanks, and techStackCards.

Rules:
- Read projectEvidenceBriefs, evidenceLedger, capabilityCards, domainRanks, and techStackCards before naming axes.
- Do not use fixed labels, examples, prelisted competency names, or server keyword buckets.
- Axis labels must be short Korean hiring-evaluation labels created from the evidence.
- Axis labels must not include source filenames, parenthetical source citations, or low-level internal mechanism names.
- Scores are calibrated 0-100 portfolio presentation estimates, not official test scores.
- Each axis must measure a distinct strength or competency proven by multiple pieces of evidence when possible.
- Keep scores realistic and relatively calibrated against the induced capabilityCards and domainRanks.
- Return only the requested JSON object.
""".strip()

RADAR_PLANNER_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["radarAxes"],
    "properties": {
        "radarAxes": {
            "type": "array",
            "minItems": 6,
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["label", "score", "reason"],
                "properties": {
                    "label": {"type": "string"},
                    "score": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "reason": {"type": "string"},
                },
            },
        },
    },
}


def normalize_radar_plan(radar_plan):
    if not isinstance(radar_plan, dict):
        return []

    radar_axes = radar_plan.get("radarAxes")

    if not isinstance(radar_axes, list):
        return []

    normalized_axes = []

    for radar_axis in radar_axes[:6]:
        if not isinstance(radar_axis, dict):
            continue

        label = clean_visible_text(radar_axis.get("label"), 24)

        if not label:
            continue

        normalized_axes.append({
            "label": label,
            "score": clamp_int(radar_axis.get("score"), 0, 100, 80),
            "reason": clean_visible_text(radar_axis.get("reason"), 180),
        })

    return normalized_axes
