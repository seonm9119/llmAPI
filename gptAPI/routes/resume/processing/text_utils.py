import re


VISIBLE_SOURCE_REFERENCE_PATTERN = re.compile(r"\([^)]*\.md[^)]*\)")
MARKDOWN_SOURCE_PATTERN = re.compile(r"[^`\"'<>:;,\[\](){}\n]+?\.md")
KEYWORD_SPLIT_PATTERN = re.compile(r"\s*(?:/|\+|,|·|\band\b|및)\s*", re.IGNORECASE)
SUMMARY_TITLE_MAX_LENGTH = 32
CAPABILITY_CARD_TITLE_MAX_LENGTH = 14
AI_DOMAIN_CARD_TITLE_MAX_LENGTH = 22
SKILL_KEYWORD_GROUP_TITLE_MAX_LENGTH = 22
TITLE_BOUNDARY_MIN_LENGTH = 10
SUMMARY_TITLE_COMPACTIONS = [
    (r"생성형\s*출력의?\s*근거를\s*임베딩\s*기반으로\s*검증해\s*회사\s*사전으로\s*안전히\s*흡수하는\s*", "생성형 출력 근거를 검증하는 "),
    (r"회사\s*사전으로\s*안전히\s*흡수하는\s*", ""),
    (r"임베딩\s*기반으로\s*", ""),
    (r"근거를\s*검증해", "근거를 검증하는"),
]
CARD_TITLE_COMPACTIONS = [
    (r"\s*[—-]\s*", " "),
    (r"\s*&\s*", " & "),
    (r"\s{2,}", " "),
]
AI_DOMAIN_TITLE_COMPACTIONS = [
    (r"검증과\s*기업\s*사전화\s*설계", "검증"),
    (r"전이·비교\s*실험과\s*불확실성\s*기반\s*서비스화", "전이·비교 실험"),
    (r"클래식\s*/\s*기하\s*기반\s*CV와\s*재현\s*가능한\s*데모\s*배포", "클래식 CV 데모"),
]
SKILL_KEYWORD_GROUP_TITLE_COMPACTIONS = [
    (r"\bDocument AI\s*&\s*LLM\s*검증\b", "Document AI·LLM 검증"),
    (r"\bMedical Imaging\s*&\s*Evaluation\b", "Medical Imaging 평가"),
    (r"\bClassical CV\s*&\s*Feature[-‑]aware Vision\b", "Classical CV"),
]
TITLE_TRAILING_CHARACTERS = " \t\r\n-–—·.,;:：/&+"

FORBIDDEN_VISIBLE_TERM_REPLACEMENTS = [
    (r"면접\s*(?:에서|시|때)?\s*(?:추가로\s*|별도로\s*)?(?:확인|검증)(?:해야\s*합니다|이\s*필요합니다|할\s*필요가\s*있습니다)\.?", "자료상 보완 설명이 필요한 영역입니다."),
    (r"면접\s*(?:에서|시|때)?\s*(?:추가로\s*|별도로\s*)?(?:확인|검증)해야\s*할\s*(?:부분|지점|영역|내용)", "자료상 보완 설명이 필요한 부분"),
    (r"면접에서\s*확인해야합니다\.?", "자료상 보완 설명이 필요한 영역입니다."),
    (r"\bQwen[0-9A-Za-z_.-]*\b", "생성형 모델"),
    (r"\bGPT\s*draft\b", "생성 결과"),
    (r"초안\s*라벨|초안", "생성 결과"),
    (r"\bkey\s*/\s*signal\b|\bkey\s*·\s*signal\b", "근거 항목"),
    (r"\bkey\b|\bsignal\b", "근거 항목"),
    (r"\bProjection[A-Za-z0-9_]*\b|\bprojection_head\b|\bprojection\b|프로젝션", "임베딩 정렬"),
    (r"\bkeep_review_drop_gate\b|\bgate\b", "검토 기준"),
    (r"\bDictionaryNormalization\b|\bdictionary_normalization\b|\bdictionary\b", "정규화 기준"),
    (r"\bT1Gd\b|\bFLAIR\b", "MRI 입력"),
    (r"\bhard[-‑]negative\b|\bhard_negative\b", "오류 대비"),
    (r"\bPrototypeLoss\b|\bprototype_loss\b|\bprototype\b", "기준 표현"),
    (r"프로토타입\s*손실", "기준 표현 학습"),
    (r"하드\s*네거티브", "오류 대비 샘플"),
    (r"\bgold-set\b|골드셋", "검증셋"),
    (r"\bmetric[-‑ ]learning\b", "거리 기반 검증"),
    (r"\bSupervisedContrastive\b|\bcontrastive\b", "대조학습"),
    (r"\b3d-force-graph\b", "3D 시각화"),
    (r"\bkeep\s*/\s*review\s*/\s*drop\b", "자동 승인·검토·보류"),
    (r"\bsubject\s*/\s*document_type\s*/\s*business_domain\s*/\s*modifier\b", "문서 분류 축"),
    (r"\bhead\b", "검증기"),
    (r"헤드", "검증기"),
    (r"게이트", "검토 기준"),
    (r"근거\s*신호\s*\(evidence\)|근거\s*신호|\(evidence\)", "근거"),
    (r"신호", "근거"),
    (r"산출문", "산출물"),
    (r"프론트워크벤치", "프론트 워크벤치"),
    (r"두번째", "두 번째"),
    (r"세번째", "세 번째"),
    (r"알고리듬", "알고리즘"),
    (r"\bforeground\b", "관심 영역"),
    (r"\bcache\b|캐시", "저장 결과"),
]


def clean_visible_text(text, max_length=None, source_names=None):
    visible_text = str(text or "").strip()
    visible_text = VISIBLE_SOURCE_REFERENCE_PATTERN.sub("", visible_text)

    if source_names:
        visible_text = remove_visible_source_names(visible_text, source_names)

    visible_text = MARKDOWN_SOURCE_PATTERN.sub("", visible_text)

    for forbidden_pattern, replacement_text in FORBIDDEN_VISIBLE_TERM_REPLACEMENTS:
        visible_text = re.sub(forbidden_pattern, replacement_text, visible_text, flags=re.IGNORECASE)

    visible_text = visible_text.replace("임베딩 정렬 임베딩 검증기", "임베딩 검증기")
    visible_text = visible_text.replace("검토 기준를", "검토 기준을")
    visible_text = visible_text.replace("생성 결과을", "생성 결과를")
    visible_text = visible_text.replace("사전(asset)", "사전 자산")
    visible_text = clean_dangling_source_punctuation(visible_text)
    visible_text = re.sub(r"\s+([.,;:!?])", r"\1", visible_text)
    visible_text = re.sub(r"\s{2,}", " ", visible_text).strip()

    if max_length:
        return visible_text[:max_length]

    return visible_text


def clean_summary_title(title, source_names=None):
    title_text = re.sub(r"^\s*(?:총평|종합\s*평가|종합평가|overall)\s*[:：]\s*", "", str(title or ""), flags=re.IGNORECASE)
    return clean_limited_title(title_text, SUMMARY_TITLE_MAX_LENGTH, source_names, SUMMARY_TITLE_COMPACTIONS, 18)


def clean_capability_card_title(title, source_names=None):
    return clean_limited_title(title, CAPABILITY_CARD_TITLE_MAX_LENGTH, source_names)


def clean_ai_domain_card_title(title, source_names=None):
    return clean_limited_title(title, AI_DOMAIN_CARD_TITLE_MAX_LENGTH, source_names, AI_DOMAIN_TITLE_COMPACTIONS)


def clean_skill_keyword_group_title(title, source_names=None):
    return clean_limited_title(title, SKILL_KEYWORD_GROUP_TITLE_MAX_LENGTH, source_names, SKILL_KEYWORD_GROUP_TITLE_COMPACTIONS)


def clean_limited_title(title, max_length, source_names=None, compactions=None, boundary_min_length=TITLE_BOUNDARY_MIN_LENGTH):
    title_text = clean_visible_text(title, source_names=source_names)

    for title_pattern, replacement_text in CARD_TITLE_COMPACTIONS:
        title_text = re.sub(title_pattern, replacement_text, title_text, flags=re.IGNORECASE)

    for title_pattern, replacement_text in compactions or []:
        title_text = re.sub(title_pattern, replacement_text, title_text, flags=re.IGNORECASE)

    title_text = re.sub(r"\s{2,}", " ", title_text).strip()
    title_text = trim_limited_title(title_text, max_length, boundary_min_length)
    title_text = re.sub(r"\s+(?:및|and)$", "", title_text, flags=re.IGNORECASE).strip()
    return title_text.strip(TITLE_TRAILING_CHARACTERS)


def trim_limited_title(title_text, max_length, boundary_min_length=TITLE_BOUNDARY_MIN_LENGTH):
    if len(title_text) <= max_length:
        return title_text

    truncated_title = title_text[:max_length].rstrip()

    if " " not in truncated_title:
        return truncated_title

    word_boundary_title = truncated_title.rsplit(" ", 1)[0].strip()

    if len(word_boundary_title) >= boundary_min_length:
        return word_boundary_title

    return truncated_title


def remove_visible_source_names(text, source_names):
    visible_text = text

    for source_name in sorted(source_names, key=len, reverse=True):
        source_name = str(source_name or "").strip()

        if not source_name:
            continue

        visible_text = re.sub(
            rf"\s*(?:,|및|and)?\s*{re.escape(source_name)}\s*(?:에서|에는|에|의|로|와|과)?",
            "",
            visible_text,
            flags=re.IGNORECASE,
        )

    return visible_text


def clean_dangling_source_punctuation(text):
    visible_text = text
    visible_text = re.sub(r",\s*,+", ",", visible_text)
    visible_text = re.sub(r"(로|으로)\s*,\s*에", r"\1", visible_text)
    visible_text = re.sub(r",\s*(?:에서|에는|에|의|로|와|과)(?=\s|$)", "", visible_text)
    visible_text = re.sub(r"\s+,", ",", visible_text)
    visible_text = re.sub(r",\s*\.", ".", visible_text)
    return visible_text


def split_atomic_keyword_labels(label):
    label_text = clean_visible_text(label)

    if not label_text:
        return []

    keyword_labels = []

    for keyword_label in KEYWORD_SPLIT_PATTERN.split(label_text):
        keyword_label = keyword_label.strip()

        if keyword_label and keyword_label not in keyword_labels:
            keyword_labels.append(keyword_label)

    return keyword_labels or [label_text]
