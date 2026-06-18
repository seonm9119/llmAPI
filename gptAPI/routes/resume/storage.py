import hashlib
import json
import time
from pathlib import Path

from .strategy import OPENAI_GENERATED_PROVIDER, REPORT_CACHE_VERSION, REPORT_SECTION_NAMES


REPORT_CACHE_PATH = Path(__file__).resolve().parents[2] / "cache" / "resume_report_cache.json"
ALLOWED_CACHE_PROVIDERS = {OPENAI_GENERATED_PROVIDER}


def build_report_cache_key(resume_context, model, report_prompt_version):
    cache_fingerprint = {
        "cacheVersion": REPORT_CACHE_VERSION,
        "model": model,
        "reportPromptVersion": report_prompt_version,
        "sourceFingerprints": build_source_fingerprints(resume_context),
    }
    cache_fingerprint_text = json.dumps(cache_fingerprint, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(cache_fingerprint_text.encode("utf-8")).hexdigest()


def read_report_cache(cache_key):
    try:
        cache_payload = json.loads(REPORT_CACHE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None

    if not isinstance(cache_payload, dict):
        return None

    if cache_payload.get("cacheKey") != cache_key:
        return None

    if cache_payload.get("cacheVersion") != REPORT_CACHE_VERSION:
        return None

    if cache_payload.get("provider") not in ALLOWED_CACHE_PROVIDERS:
        return None

    report = cache_payload.get("report")

    if not is_complete_report(report):
        return None

    return cache_payload


def write_report_cache(cache_key, provider, model, report):
    if provider not in ALLOWED_CACHE_PROVIDERS:
        raise ValueError(f"refuse to cache non-OpenAI resume report provider: {provider}")

    if not is_complete_report(report):
        raise ValueError("refuse to cache incomplete resume report.")

    cache_payload = {
        "cacheKey": cache_key,
        "cacheVersion": REPORT_CACHE_VERSION,
        "provider": provider,
        "model": model,
        "generatedAt": int(time.time()),
        "report": report,
    }
    temporary_cache_path = REPORT_CACHE_PATH.with_suffix(".tmp")

    REPORT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_cache_path.write_text(json.dumps(cache_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_cache_path.replace(REPORT_CACHE_PATH)
    return cache_payload


def build_source_fingerprints(resume_context):
    source_fingerprints = []

    for source in collect_cache_sources(resume_context):
        source_name = str(source.get("name") or "").strip()
        source_content = str(source.get("content") or "")

        if not source_name:
            continue

        source_fingerprints.append({
            "name": source_name,
            "length": len(source_content),
            "sha256": hashlib.sha256(source_content.encode("utf-8")).hexdigest(),
        })

    return sorted(source_fingerprints, key=lambda source_fingerprint: source_fingerprint["name"])


def collect_cache_sources(resume_context):
    if not isinstance(resume_context, dict):
        return []

    cache_sources = []
    project_index_source = resume_context.get("projectIndexSource")

    if isinstance(project_index_source, dict):
        cache_sources.append(project_index_source)

    project_detail_sources = resume_context.get("projectDetailSources")

    if isinstance(project_detail_sources, list):
        cache_sources.extend(source for source in project_detail_sources if isinstance(source, dict))

    return cache_sources


def is_complete_report(report):
    if not isinstance(report, dict):
        return False

    for section_name in REPORT_SECTION_NAMES:
        if section_name not in report:
            return False

    summary = report.get("summary")

    if not isinstance(summary, dict):
        return False

    return bool(summary.get("title") and summary.get("description"))
