import hashlib
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from client import create_structured_response
from config import GPT_MODEL

router = APIRouter(prefix="/brain-mri/segmentation")

PROMPT_VERSION = "brain-mri-segmentation-interpretation-v2"
INTERPRETATION_CACHE_PATH = Path("/app/cache/brain_mri_interpretation_cache.json")
INTERPRETATION_CACHE = None

BRAIN_MRI_SYSTEM_PROMPT = """
You write concise Korean clinical-style interpretation text for a brain tumor segmentation portfolio demo.
Use only the supplied quantitative values. Do not diagnose. Do not claim the model replaces clinicians.
Write for medical-company interview reviewers who understand healthcare but may not inspect the code.
All visible text must be Korean except accepted abbreviations such as WT, TC, ET, Dice, HD95, MRI, and mL.
Convert ratios to percentages with one decimal place when writing visible text: 0.033 should be written as 3.3%.
Do not expose JSON field names such as probabilityMean, highRatio, tcWtRatio, or brainRatio.
Use clear Korean terms: 전체 종양 영향 영역(WT), 종양 중심부(TC), 조영증강 활성 영역(ET), 예측 불확실성.
Keep the tone professional, clear, and useful.
""".strip()

BRAIN_MRI_INTERPRETATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "headline",
        "summary",
        "regionFinding",
        "compositionFinding",
        "uncertaintyFinding",
        "clinicalCaution",
    ],
    "properties": {
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "regionFinding": {"type": "string"},
        "compositionFinding": {"type": "string"},
        "uncertaintyFinding": {"type": "string"},
        "clinicalCaution": {"type": "string"},
    },
}


@router.post("/interpret")
async def interpret_brain_mri_segmentation(request: Request):
    request_payload = await request.json()
    case_id = str(request_payload.get("caseId") or "").strip()
    model_title = str(request_payload.get("modelTitle") or "").strip()
    quantitative_summary = request_payload.get("quantitativeSummary")
    score_context = request_payload.get("scoreContext") or {}
    heatmap_context = request_payload.get("heatmapContext") or {}

    if not case_id:
        raise HTTPException(status_code=400, detail="caseId is required.")

    if not isinstance(quantitative_summary, dict):
        raise HTTPException(status_code=400, detail="quantitativeSummary is required.")

    compact_payload = build_compact_payload(case_id, model_title, quantitative_summary, score_context, heatmap_context)
    cache_key = make_cache_key(compact_payload)
    interpretation_cache = get_interpretation_cache()

    if cache_key in interpretation_cache:
        cached_interpretation = interpretation_cache[cache_key]
        cached_interpretation["cached"] = True
        cached_interpretation["cacheType"] = "disk"
        return cached_interpretation

    try:
        interpretation, raw_text = create_structured_response(
            BRAIN_MRI_SYSTEM_PROMPT,
            compact_payload,
            BRAIN_MRI_INTERPRETATION_SCHEMA,
            model=GPT_MODEL,
        )
    except Exception as openai_error:
        raise HTTPException(
            status_code=502,
            detail={
                "message": str(openai_error),
                "provider": "openai",
                "model": GPT_MODEL,
            },
        )

    response_payload = {
        "success": True,
        "provider": "openai",
        "model": GPT_MODEL,
        "cached": False,
        "cacheType": "miss",
        "promptVersion": PROMPT_VERSION,
        "caseId": case_id,
        "modelTitle": model_title,
        "interpretation": interpretation,
        "rawText": raw_text,
    }
    save_interpretation_cache_entry(cache_key, response_payload)

    return response_payload


def build_compact_payload(case_id, model_title, quantitative_summary, score_context, heatmap_context):
    regions = quantitative_summary.get("regions") or {}
    composition = quantitative_summary.get("composition") or {}
    uncertainty = quantitative_summary.get("uncertainty") or {}

    return {
        "task": "Write a Korean explanation of the case-level segmentation result.",
        "promptVersion": PROMPT_VERSION,
        "caseId": case_id,
        "modelTitle": model_title,
        "regions": {
            "WT": compact_region(regions.get("wt")),
            "TC": compact_region(regions.get("tc")),
            "ET": compact_region(regions.get("et")),
        },
        "brainForeground": {
            "volumeMl": round_number((quantitative_summary.get("brainForeground") or {}).get("volumeMl")),
        },
        "composition": {
            "tcWtRatio": round_number(composition.get("tcWtRatio")),
            "etTcRatio": round_number(composition.get("etTcRatio")),
            "etWtRatio": round_number(composition.get("etWtRatio")),
            "edemaRelatedWtRatio": round_number((composition.get("edemaRelated") or {}).get("wtRatio")),
            "nonEnhancingCoreTcRatio": round_number((composition.get("nonEnhancingCore") or {}).get("tcRatio")),
        },
        "uncertainty": {
            "probabilityMean": round_number((uncertainty.get("probability") or {}).get("mean")),
            "probabilityHighRatio": round_number((uncertainty.get("probability") or {}).get("highRatio")),
            "ttaMean": round_number((uncertainty.get("tta") or {}).get("mean")),
            "ttaHighRatio": round_number((uncertainty.get("tta") or {}).get("highRatio")),
        },
        "scoreContext": score_context,
        "heatmapContext": heatmap_context,
        "style": {
            "language": "ko-KR",
            "sentenceCount": "4 to 6 short sentences across fields",
            "avoid": ["diagnosis", "treatment recommendation", "clinician replacement claim"],
        },
    }


def compact_region(region_summary):
    region_summary = region_summary or {}

    return {
        "volumeMl": round_number(region_summary.get("volumeMl")),
        "brainRatio": round_number(region_summary.get("brainRatio")),
        "meanProbability": round_number(region_summary.get("meanProbability")),
    }


def round_number(number_value):
    try:
        numeric_value = float(number_value)
    except (TypeError, ValueError):
        return None

    return round(numeric_value, 4)


def get_interpretation_cache():
    global INTERPRETATION_CACHE

    if INTERPRETATION_CACHE is None:
        INTERPRETATION_CACHE = load_interpretation_cache()

    return INTERPRETATION_CACHE


def load_interpretation_cache():
    try:
        if not INTERPRETATION_CACHE_PATH.exists():
            return {}

        with INTERPRETATION_CACHE_PATH.open("r", encoding="utf-8") as cache_file:
            cache_data = json.load(cache_file)

        if not isinstance(cache_data, dict):
            return {}

        return {
            str(cache_key): interpretation
            for cache_key, interpretation in cache_data.items()
            if isinstance(interpretation, dict)
        }
    except (OSError, json.JSONDecodeError):
        return {}


def save_interpretation_cache_entry(cache_key, interpretation):
    interpretation_cache = get_interpretation_cache()
    interpretation_cache[cache_key] = interpretation
    write_interpretation_cache(interpretation_cache)


def write_interpretation_cache(interpretation_cache):
    temp_cache_path = INTERPRETATION_CACHE_PATH.with_suffix(f"{INTERPRETATION_CACHE_PATH.suffix}.tmp")

    try:
        INTERPRETATION_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

        with temp_cache_path.open("w", encoding="utf-8") as cache_file:
            json.dump(interpretation_cache, cache_file, ensure_ascii=False, indent=2, sort_keys=True)

        temp_cache_path.replace(INTERPRETATION_CACHE_PATH)
    except OSError:
        pass


def make_cache_key(compact_payload):
    cache_payload = {
        "promptVersion": PROMPT_VERSION,
        "model": GPT_MODEL,
        "payload": compact_payload,
    }
    cache_text = json.dumps(cache_payload, ensure_ascii=False, sort_keys=True)

    return hashlib.sha256(cache_text.encode("utf-8")).hexdigest()
