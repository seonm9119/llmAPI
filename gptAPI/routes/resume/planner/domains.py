from .common import clamp_int, normalize_markdown_evidence


DOMAIN_PLANNER_PROMPT_VERSION = "resume-domain-planner-v3"

DOMAIN_PLANNER_SYSTEM_PROMPT = """
You are the domain-rank planner for "AI 분야별 강점".
Choose the Top 3 AI domains from all project markdown evidence. Do not use a fixed template.

Ranking criteria:
- repeated project evidence
- depth of implementation
- evaluation quality
- service-facing proof
- interviewer relevance for Applied AI roles

Rules:
- Read every projectEvidenceBriefs item before ranking.
- Use evidenceLedger first to see repeated domain, evaluation, service, and limitation signals.
- Step 1: select the Top 3 AI fields where this candidate is most convincingly positioned.
- Step 2: evaluate the full markdown evidence again through each selected field.
- Rank the domains by evidence strength, not by what sounds fashionable.
- Headlines must sound like hiring judgement, not feature labels.
- Each reason must be one strong Korean paragraph, not a bullet list or labelled fields.
- Each reason must explain the domain problem, the candidate's problem-solving approach, why that approach is strong from an evaluator's view, and where the approach can expand in real work.
- Do not write limitation or verification-gap sentences in domain reasons. Domain cards are strength-positioning cards.
- Do not merely list projects, models, libraries, or metrics. Use them only as evidence for the approach.
- Each reason must be roughly 260-520 Korean characters and compare the approach against a typical junior-to-mid Applied AI applicant.
- The ranking must change when the projects folder evidence changes.
- Evidence labels must be bare `.md` filenames only.
- Visible reasons must not mention md files, markdown, project folders, projectEvidenceBriefs, or evidenceLedger.
- Do not call the candidate "이 사람"; use "지원자" sparingly or write with the domain strength as the sentence subject.
- Return only the requested JSON object.
""".strip()

DOMAIN_PLANNER_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["domainRanks"],
    "properties": {
        "domainRanks": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["rank", "domain", "headline", "reason", "evidence"],
                "properties": {
                    "rank": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 3,
                    },
                    "domain": {"type": "string"},
                    "headline": {"type": "string"},
                    "reason": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 3,
                        "items": {"type": "string"},
                    },
                },
            },
        },
    },
}


def normalize_domain_plan(domain_plan, allowed_source_names=None):
    if not isinstance(domain_plan, dict):
        return []

    domain_ranks = domain_plan.get("domainRanks")

    if not isinstance(domain_ranks, list):
        return []

    normalized_domains = []

    for domain_index, domain_rank in enumerate(domain_ranks[:3], start=1):
        if not isinstance(domain_rank, dict):
            continue

        domain = str(domain_rank.get("domain") or "").strip()
        headline = str(domain_rank.get("headline") or "").strip()
        reason = str(domain_rank.get("reason") or "").strip()

        if not domain or not headline or not reason:
            continue

        normalized_domains.append({
            "rank": clamp_int(domain_rank.get("rank"), 1, 3, domain_index),
            "domain": domain[:80],
            "headline": headline[:140],
            "reason": reason[:720],
            "evidence": normalize_markdown_evidence(domain_rank.get("evidence"), allowed_source_names, 3),
        })

    normalized_domains.sort(key=lambda domain_rank: domain_rank["rank"])
    return normalized_domains
