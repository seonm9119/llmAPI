import re

from .text_utils import (
    clean_ai_domain_card_title,
    clean_capability_card_title,
    clean_skill_keyword_group_title,
    clean_summary_title,
    clean_visible_text,
    split_atomic_keyword_labels,
)


MARKDOWN_SOURCE_PATTERN = re.compile(r"[^`\"'<>:;,\[\](){}\n]+?\.md")


def normalize_openai_report(report, allowed_source_names):
    if not isinstance(report, dict):
        return {}

    return {
        "summary": normalize_summary(report.get("summary"), allowed_source_names),
        "capabilities": normalize_capabilities(report.get("capabilities"), allowed_source_names),
        "radar": normalize_radar(report.get("radar"), allowed_source_names),
        "skills": normalize_skills(report.get("skills"), allowed_source_names),
        "domains": normalize_domains(report.get("domains"), allowed_source_names),
        "skillKeywords": normalize_skill_keyword_groups(report.get("skillKeywords"), allowed_source_names),
        "sources": normalize_sources(report.get("sources"), allowed_source_names),
    }


def normalize_summary(summary, allowed_source_names):
    if not isinstance(summary, dict):
        return {}

    return {
        "title": clean_summary_title(summary.get("title"), allowed_source_names),
        "description": clean_summary_description(summary.get("description"), allowed_source_names),
    }


def normalize_capabilities(capabilities, allowed_source_names):
    if not isinstance(capabilities, list):
        return []

    normalized_capabilities = []
    allowed_grades = {"상", "중상", "중", "하"}
    allowed_tones = {"blue", "green", "amber", "coral"}

    for capability in capabilities[:4]:
        if not isinstance(capability, dict):
            continue

        label = clean_capability_card_title(capability.get("label"), allowed_source_names)
        summary = clean_visible_text(capability.get("summary"), 600, allowed_source_names)

        if not label or not summary:
            continue

        grade = str(capability.get("grade") or "").strip()
        tone = str(capability.get("tone") or "").strip()

        normalized_capabilities.append({
            "label": label,
            "grade": grade if grade in allowed_grades else "중상",
            "summary": summary,
            "evidence": normalize_markdown_evidence(capability.get("evidence"), allowed_source_names, 3),
            "tone": tone if tone in allowed_tones else "blue",
        })

    return normalized_capabilities


def normalize_radar(radar_items, allowed_source_names):
    if not isinstance(radar_items, list):
        return []

    normalized_radar_items = []

    for radar_item in radar_items:
        if not isinstance(radar_item, dict):
            continue

        label = clean_visible_text(radar_item.get("label"), 24, allowed_source_names)

        if not label:
            continue

        normalized_radar_items.append({
            "label": label[:24],
            "score": clamp_int(radar_item.get("score"), 0, 100, 80),
        })

    return normalized_radar_items[:6]


def normalize_skills(skills, allowed_source_names):
    if not isinstance(skills, list):
        return []

    normalized_skills = []

    for skill in skills[:4]:
        if not isinstance(skill, dict):
            continue

        title = clean_visible_text(skill.get("title"), 80, allowed_source_names)
        description = clean_visible_text(skill.get("description"), 700, allowed_source_names)

        if not title or not description:
            continue

        normalized_skills.append({
            "title": title,
            "description": description,
            "evidence": ", ".join(normalize_markdown_evidence(skill.get("evidence"), allowed_source_names, 3)),
        })

    return normalized_skills


def normalize_domains(domains, allowed_source_names):
    if not isinstance(domains, list):
        return []

    normalized_domains = []

    for domain_index, domain in enumerate(domains[:3], start=1):
        if not isinstance(domain, dict):
            continue

        domain_name = clean_ai_domain_card_title(domain.get("domain"), allowed_source_names)
        headline = clean_visible_text(domain.get("headline"), 140, allowed_source_names)
        reason = clean_visible_text(domain.get("reason"), 900, allowed_source_names)

        if not domain_name or not headline or not reason:
            continue

        normalized_domains.append({
            "rank": clamp_int(domain.get("rank"), 1, 3, domain_index),
            "domain": domain_name,
            "headline": headline,
            "reason": reason,
            "evidence": normalize_markdown_evidence(domain.get("evidence"), allowed_source_names, 3),
        })

    normalized_domains.sort(key=lambda domain: domain["rank"])
    return normalized_domains


def normalize_skill_keyword_groups(skill_keyword_groups, allowed_source_names):
    if not isinstance(skill_keyword_groups, list):
        return []

    normalized_groups = []

    for skill_keyword_group in skill_keyword_groups:
        if not isinstance(skill_keyword_group, dict):
            continue

        category = clean_skill_keyword_group_title(skill_keyword_group.get("category"), allowed_source_names)
        keywords = normalize_skill_keywords(skill_keyword_group.get("keywords"))

        if category and keywords:
            normalized_groups.append({
                "category": category,
                "keywords": keywords,
            })

    return normalized_groups[:4]


def normalize_skill_keywords(skill_keywords):
    if not isinstance(skill_keywords, list):
        return []

    normalized_keywords = []
    allowed_tones = {"blue", "green", "amber", "coral"}
    allowed_strengths = {"strong", "medium", "weak"}

    for skill_keyword in skill_keywords:
        if not isinstance(skill_keyword, dict):
            continue

        tone = str(skill_keyword.get("tone") or "").strip()
        strength = str(skill_keyword.get("strength") or "").strip()

        for label in split_atomic_keyword_labels(skill_keyword.get("label")):
            if not label:
                continue

            normalized_keywords.append({
                "label": label[:56],
                "tone": tone if tone in allowed_tones else "blue",
                "strength": strength if strength in allowed_strengths else "medium",
                "weight": normalize_keyword_weight(skill_keyword.get("weight")),
            })

    normalized_keywords.sort(key=lambda keyword: keyword["weight"], reverse=True)
    return normalized_keywords


def normalize_sources(sources, allowed_source_names):
    normalized_source_names = normalize_markdown_evidence(sources, allowed_source_names, 8)

    return [
        {
            "name": source_name,
            "reason": "",
        }
        for source_name in normalized_source_names
    ]


def normalize_markdown_evidence(evidence_items, allowed_source_names, limit):
    if isinstance(evidence_items, list):
        raw_evidence_items = evidence_items
    else:
        raw_evidence_items = [evidence_items]

    allowed_markdown_source_names = [
        normalize_markdown_source_name(source_name)
        for source_name in allowed_source_names
    ]
    allowed_markdown_source_names = [
        source_name
        for source_name in allowed_markdown_source_names
        if source_name
    ]
    normalized_evidence = []

    for raw_evidence_item in raw_evidence_items:
        evidence_text = str(raw_evidence_item or "").strip()

        for source_name in allowed_markdown_source_names:
            if source_name in evidence_text and source_name not in normalized_evidence:
                normalized_evidence.append(source_name)

        for evidence_match in MARKDOWN_SOURCE_PATTERN.finditer(evidence_text):
            source_name = normalize_markdown_source_name(evidence_match.group(0))

            if source_name in allowed_markdown_source_names and source_name not in normalized_evidence:
                normalized_evidence.append(source_name)

    return normalized_evidence[:limit]


def normalize_markdown_source_name(source_name):
    source_text = str(source_name or "").strip().strip("`\"'<>")

    if not source_text:
        return ""

    source_text = source_text.replace("\\", "/")
    markdown_extension_index = source_text.lower().find(".md")

    if markdown_extension_index < 0:
        return ""

    source_text = source_text[:markdown_extension_index + 3]

    if "/" in source_text:
        source_text = source_text.rsplit("/", 1)[-1]

    source_text = source_text.strip(" \t\r\n-•.,;:()[]{}'\"`")
    return source_text if source_text.lower().endswith(".md") else ""


def clean_summary_description(description, allowed_source_names):
    summary_description = str(description or "").strip()
    summary_description = re.sub(r"^\s*(?:총평|종합\s*평가|종합평가|overall)\s*[:：]\s*", "", summary_description, flags=re.IGNORECASE)
    return clean_visible_text(summary_description, source_names=allowed_source_names)


def normalize_keyword_weight(weight):
    keyword_weight = clamp_int(weight, 0, 100, 50)

    if 0 < keyword_weight <= 10:
        return keyword_weight * 10

    return keyword_weight


def clamp_int(number, minimum, maximum, default_number):
    try:
        parsed_number = int(number)
    except (TypeError, ValueError):
        parsed_number = default_number

    return max(minimum, min(maximum, parsed_number))
