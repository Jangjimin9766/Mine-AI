from app.core.llm_client import llm_client
import json
import os
import re
import time
import uuid
from urllib.parse import parse_qs, urlparse
from app.core.searcher import search_with_tavily, scrape_with_jina, extract_images_from_content, get_topic_fallback_images, scrape_multiple_with_jina, scrape_labeled_sources, validate_image_url, search_with_pexels_metadata, pexels_dedupe_key
from app.core.prompts import MAGAZINE_SYSTEM_PROMPT_V8
from app.core.utils import is_mostly_english, translate_to_korean, force_translate_magazine_json
from concurrent.futures import ThreadPoolExecutor
import threading


def _runtime_commit() -> str:
    return (
        os.getenv("GIT_COMMIT")
        or os.getenv("APP_VERSION")
        or os.getenv("RUNPOD_IMAGE_TAG")
        or "unknown"
    )


DEFAULT_IMAGE_KEYWORDS_BY_TAG = {
    "FASHION": "fashion editorial outfit",
    "BEAUTY": "beauty skincare products",
    "ACCESSORY": "luxury accessories detail",
    "DESIGN": "modern design objects",
    "INTERIOR": "modern home interior",
    "MUSIC": "music studio headphones",
    "ART": "gallery art objects",
    "READING": "books reading desk",
    "OTT": "movie streaming screen",
    "DRAMA": "cinematic drama scene",
    "MOVIE": "cinema film scene",
    "SCIENCE": "science laboratory detail",
    "CULTURE": "cultural city scene",
    "EDUCATION": "study desk books",
    "MINIMALISM": "minimal desk setup",
    "RETRO": "retro vintage objects",
    "VINTAGE": "vintage lifestyle objects",
    "TREND": "trend lifestyle flatlay",
    "WEATHER": "weather landscape sky",
    "SPORTS": "sports equipment action",
    "FITNESS": "fitness workout equipment",
    "TRAVEL": "travel destination landscape",
    "CAMPING": "camping outdoor gear",
    "HIKING": "hiking mountain trail",
    "ENVIRONMENT": "green nature landscape",
    "ARCHITECTURE": "modern architecture detail",
    "PHOTOGRAPHY": "camera photography setup",
    "IT": "modern office technology",
    "ELECTRONICS": "consumer electronics desk",
    "GAME": "gaming desk setup",
    "PLANT": "indoor plants interior",
    "PSYCHOLOGY": "calm wellness journal",
    "FINANCE": "finance desk charts",
    "INVESTMENT": "investment charts desk",
    "LIFESTYLE": "premium lifestyle flatlay",
    "FOOD": "food table detail",
    "HEALTH": "healthy wellness objects",
    "TECH": "modern office technology",
}

EDUCATIONAL_TITLE_TERMS = (
    "개념", "개념 설명", "개념 다지기", "이점", "장점", "효과", "환경 이점",
    "실전", "실전 워크플로우", "워크플로우", "실천 방법", "기대 효과",
    "핵심 포인트", "활용법", "추천 기준", "가이드", "방법론",
)

PLACEHOLDER_TITLE_PATTERNS = (
    r"^매거진\s*제목$",
    r"^섹션\s*\d*\s*제목$",
    r"^섹션\s*\d+\s*요약$",
    r"^문단\s*소제목$",
    r"^소제목\s*\d+$",
)

NOISY_SOURCE_HOST_TERMS = (
    "github.com",
    "gitlab.com",
    "stackoverflow.com",
    "health.kr",
)

NOISY_SOURCE_PATH_TERMS = (
    ".php",
    ".json",
    "/ajax/",
    "/api/",
    "/blob/",
)

EDITORIAL_HEADING_FALLBACKS = (
    "매일 손에 닿는 선택",
    "오래 쓰이는 물성의 기준",
)

PARAGRAPH_MIN_CHARS = 250
PARAGRAPH_MAX_CHARS = 550
TARGETED_EXPANSION_MAX_ITEMS = 3
PARAGRAPH_LENGTH_METRIC = "python_len_text_including_spaces_and_markdown"
ENTITY_RECOMMENDATION_TERMS = [
    "추천", "recommend", "recommendation", "유튜버", "youtuber", "youtube",
    "채널", "creator", "크리에이터", "인플루언서", "맛집", "장소", "브랜드",
    "인물", "사람", "전문가", "계정", "account", "best", "top"
]

ALLOWED_MAGAZINE_TAGS = set(DEFAULT_IMAGE_KEYWORDS_BY_TAG.keys())
TOPIC_TAG_RULES = (
    (("패션", "fashion", "옷", "코디"), "FASHION"),
    (("뷰티", "beauty", "피부", "화장품"), "BEAUTY"),
    (("액세서리", "시계", "가방", "신발"), "ACCESSORY"),
    (("디자인", "design"), "DESIGN"),
    (("인테리어", "interior", "홈", "집", "공간"), "INTERIOR"),
    (("음악", "노래", "팝송", "재즈", "힙합", "앨범"), "MUSIC"),
    (("예술", "미술", "art"), "ART"),
    (("독서", "책", "서점"), "READING"),
    (("드라마",), "DRAMA"),
    (("영화", "시네마"), "MOVIE"),
    (("과학",), "SCIENCE"),
    (("문화",), "CULTURE"),
    (("교육", "취업", "학과"), "EDUCATION"),
    (("미니멀",), "MINIMALISM"),
    (("레트로",), "RETRO"),
    (("빈티지",), "VINTAGE"),
    (("트렌드",), "TREND"),
    (("날씨",), "WEATHER"),
    (("스포츠", "야구", "축구", "농구", "테니스", "wbc", "아스날"), "SPORTS"),
    (("운동", "러닝", "헬스", "fitness"), "FITNESS"),
    (("여행", "travel", "명소", "제주", "부산", "다낭"), "TRAVEL"),
    (("캠핑",), "CAMPING"),
    (("등산", "하이킹"), "HIKING"),
    (("환경", "친환경", "지속가능"), "ENVIRONMENT"),
    (("건축",), "ARCHITECTURE"),
    (("사진", "카메라"), "PHOTOGRAPHY"),
    (("개발", "소프트웨어", "프로그래밍"), "IT"),
    (("전자", "노트북", "맥북", "애플", "기기"), "ELECTRONICS"),
    (("게임", "gaming"), "GAME"),
    (("식물",), "PLANT"),
    (("심리",), "PSYCHOLOGY"),
    (("금융",), "FINANCE"),
    (("투자", "etf"), "INVESTMENT"),
    (("음식", "food", "맛집", "요리", "레시피", "커피", "햄버거", "파스타", "김치"), "FOOD"),
    (("건강", "의학"), "HEALTH"),
    (("기술", "테크", "tech", "인공지능"), "TECH"),
)
DEFAULT_FORBIDDEN_VISUALS = [
    "low quality",
    "blurry",
    "tiny image",
    "thumbnail",
    "watermark",
    "logo",
    "text overlay",
    "duplicate image",
    "fallback placeholder",
]


def _requires_verified_sources(text: str) -> bool:
    normalized = (text or "").lower()
    return any(term in normalized for term in ENTITY_RECOMMENDATION_TERMS)


MOODBOARD_SEED_BOILERPLATE_TERMS = (
    "posted", "login", "naver", "blog", "copyright", "로그인", "네이버",
    "블로그", "댓글", "공유", "구독", "지면보기", "회원가입",
)


def _moodboard_seed_keywords(topic: str, search_results: list, labeled_sources: list, max_items: int = 6) -> list:
    keywords = []
    seen = set()

    def add(value, max_len: int = 64):
        text = str(value or "").strip()
        if not text:
            return
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"\s+", " ", text)[:max_len]
        normalized = text.lower()
        if normalized in MOODBOARD_SEED_BOILERPLATE_TERMS:
            return
        if any(term in normalized for term in MOODBOARD_SEED_BOILERPLATE_TERMS):
            return
        if normalized not in seen:
            seen.add(normalized)
            keywords.append(text)

    add(topic)
    for result in search_results or []:
        add(result.get("title"))
        if len(keywords) >= max_items:
            return keywords[:max_items]
    for result in search_results or []:
        add(result.get("content"), max_len=48)
        if len(keywords) >= max_items:
            return keywords[:max_items]
    return keywords[:max_items]

MAGAZINE_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "mine_magazine_create_response",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "tags", "cover_image_url", "sections"],
            "properties": {
                "title": {"type": "string"},
                "tags": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 4,
                    "items": {"type": "string"},
                },
                "cover_image_url": {"type": ["string", "null"]},
                "sections": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 2,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["heading", "thumbnail_url", "paragraphs", "display_order"],
                        "properties": {
                            "heading": {"type": "string"},
                            "thumbnail_url": {"type": ["string", "null"]},
                            "display_order": {"type": "integer"},
                            "paragraphs": {
                                "type": "array",
                                "minItems": 3,
                                "maxItems": 3,
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "required": [
                                        "subtitle", "text", "image_search_keyword",
                                        "source_url", "image_url"
                                    ],
                                    "properties": {
                                        "subtitle": {"type": "string"},
                                        # OpenAI Structured Outputs does not reliably support
                                        # every JSON Schema validation keyword across models.
                                        # Keep length enforcement in prompt + Python checks.
                                        "text": {
                                            "type": "string",
                                            "description": (
                                                "Korean magazine paragraph body. Must be 250-550 characters "
                                                "by Python len(text), at least 6 complete Korean sentences, "
                                                "written as dense prose without bullets or markdown emphasis. "
                                                "Use the flow: scene observation -> concrete source detail -> "
                                                "editorial context -> sensory closing impression. "
                                                "Sub-220 character summaries are invalid."
                                            ),
                                        },
                                        "image_search_keyword": {"type": "string"},
                                        "source_url": {"type": "string"},
                                        "image_url": {"type": ["string", "null"]},
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    },
}

STRUCTURAL_REPAIR_REASONS = {
    "invalid_json_schema",
    "section_count_mismatch",
    "paragraph_count_mismatch",
    "missing_required_field",
}


def _strip_source_markers(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"\n?\s*\[source_url\]:\s*https?://\S+\s*", "", text)
    text = re.sub(r"\n?\s*출처\s*:\s*https?://\S+\s*", "", text)
    return text.strip()


def _paragraph_length(text: str) -> int:
    """Production length metric: Python len(text), including spaces and Markdown chars."""
    return len(text or '')


def _paragraph_lengths(result_json: dict) -> list:
    if not isinstance(result_json, dict):
        return []
    lengths = []
    for section in result_json.get('sections', []):
        for para in section.get('paragraphs', []):
            lengths.append(_paragraph_length(para.get('text') if isinstance(para, dict) else ''))
    return lengths


def _fallback_image_keyword(tags: list, topic: str, section_heading: str) -> str:
    for tag in tags or []:
        keyword = DEFAULT_IMAGE_KEYWORDS_BY_TAG.get(str(tag).upper())
        if keyword:
            return keyword
    if is_mostly_english(topic):
        base = topic
    else:
        base = "premium lifestyle"
    if section_heading and is_mostly_english(section_heading):
        base = section_heading
    words = re.findall(r"[A-Za-z]+", base.lower())[:3]
    return " ".join(words) if len(words) >= 2 else "premium lifestyle editorial"


def _topic_default_tags(topic: str) -> list:
    text = (topic or "").lower()
    tags = [tag for keywords, tag in TOPIC_TAG_RULES if any(keyword in text for keyword in keywords)]
    if not tags:
        tags = ["LIFESTYLE", "TREND"]
    return tags[:2]


def _normalize_topic_tags(tags: list, topic: str, result_json: dict = None) -> list:
    topic_tags = _topic_default_tags(topic)
    context_parts = []
    if isinstance(result_json, dict):
        context_parts.append(str(result_json.get("title") or ""))
        context_parts.extend(
            str(section.get("heading") or "")
            for section in result_json.get("sections", [])
            if isinstance(section, dict)
        )
    relevant = topic_tags
    if topic_tags == ["LIFESTYLE", "TREND"] and context_parts:
        relevant = _topic_default_tags(" ".join(context_parts))
    if relevant == ["LIFESTYLE", "TREND"]:
        return relevant
    supplied = [
        str(tag).upper()
        for tag in tags or []
        if str(tag).upper() in ALLOWED_MAGAZINE_TAGS
    ]
    ordered = [tag for tag in supplied if tag in relevant]
    ordered.extend(tag for tag in relevant if tag not in ordered)
    return ordered[:4]


def _topic_visual_keywords(topic: str, tags: list = None) -> list:
    keyword = _fallback_image_keyword(tags or _topic_default_tags(topic), topic, "")
    words = re.findall(r"[A-Za-z][A-Za-z0-9'-]*", keyword)
    if len(words) >= 2:
        return words[:6]
    if is_mostly_english(topic or ""):
        topic_words = re.findall(r"[A-Za-z][A-Za-z0-9'-]*", topic)
        if topic_words:
            return topic_words[:6]
    return ["premium", "lifestyle", "editorial"]


def _default_magazine_plan(topic: str, existing_result: dict = None) -> dict:
    tags = _topic_default_tags(topic)
    headings = []
    if isinstance(existing_result, dict):
        headings = [
            section.get("heading")
            for section in existing_result.get("sections", [])
            if isinstance(section, dict) and section.get("heading")
        ]
    if not headings:
        headings = [_editorial_heading_fallback(topic, 0), _editorial_heading_fallback(topic, 1)]
    visual_keywords = _topic_visual_keywords(topic, tags)
    return {
        "title": f"{topic} 매거진" if topic else "M:ine 매거진",
        "tags": tags,
        "section_headings": headings[:2],
        "visual_keywords": visual_keywords,
        "moodboard_subjects": visual_keywords[:5],
        "forbidden_visuals": DEFAULT_FORBIDDEN_VISUALS,
    }


def _normalize_magazine_plan(plan: dict, topic: str, existing_result: dict = None) -> dict:
    defaults = _default_magazine_plan(topic, existing_result)
    if not isinstance(plan, dict):
        return defaults
    normalized = {**defaults, **{key: value for key, value in plan.items() if value}}
    tags = [str(tag).upper() for tag in normalized.get("tags", []) if str(tag).upper() in ALLOWED_MAGAZINE_TAGS]
    normalized["tags"] = tags[:4] or defaults["tags"]
    for key in ("section_headings", "visual_keywords", "moodboard_subjects", "forbidden_visuals"):
        values = normalized.get(key)
        normalized[key] = [str(value).strip() for value in values if str(value).strip()] if isinstance(values, list) else defaults[key]
        if not normalized[key]:
            normalized[key] = defaults[key]
    normalized["title"] = str(normalized.get("title") or defaults["title"]).strip() or defaults["title"]
    return normalized


def _section_thumbnail_query(topic: str, section: dict) -> str:
    paragraphs = section.get('paragraphs', []) if isinstance(section, dict) else []
    for para in paragraphs:
        keyword = str(para.get('image_search_keyword') or '').strip() if isinstance(para, dict) else ''
        words = re.findall(r"[A-Za-z][A-Za-z0-9'-]*", keyword)
        if len(words) >= 2:
            return " ".join(words[:6])
    return _fallback_image_keyword([], topic, section.get('heading', '') if isinstance(section, dict) else '')


def _looks_educational_title(value: str) -> bool:
    text = str(value or '').strip()
    if not text:
        return False
    return any(term in text for term in EDUCATIONAL_TITLE_TERMS)

def _looks_placeholder_title(value: str) -> bool:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return any(re.fullmatch(pattern, text, re.IGNORECASE) for pattern in PLACEHOLDER_TITLE_PATTERNS)


def _is_noisy_source_url(url: str) -> bool:
    normalized = str(url or "").lower()
    return (
        any(term in normalized for term in NOISY_SOURCE_HOST_TERMS)
        or any(term in normalized for term in NOISY_SOURCE_PATH_TERMS)
    )


def _filter_research_results(search_results: list) -> list:
    return [
        result
        for result in search_results or []
        if isinstance(result, dict) and not _is_noisy_source_url(result.get("url", ""))
    ]


def _editorial_heading_fallback(topic: str, section_idx: int) -> str:
    if topic and "텀블러" in topic:
        options = ("매일 들고 나가는 온도", "버려지지 않는 컵의 조건")
        return options[min(section_idx, len(options) - 1)]
    if topic and any(word in topic for word in ("환경", "친환경", "지속가능")):
        options = ("일상에 남는 작은 선택", "오래 쓰이는 물성의 기준")
        return options[min(section_idx, len(options) - 1)]
    return EDITORIAL_HEADING_FALLBACKS[min(section_idx, len(EDITORIAL_HEADING_FALLBACKS) - 1)]


def _sanitize_editorial_titles(result_json: dict, topic: str) -> dict:
    if not isinstance(result_json, dict):
        return result_json
    for s_idx, section in enumerate(result_json.get('sections', [])):
        if not isinstance(section, dict):
            continue
        if _looks_educational_title(section.get('heading', '')) or _looks_placeholder_title(section.get('heading', '')):
            original = section.get('heading', '')
            section['heading'] = _editorial_heading_fallback(topic, s_idx)
            print(f"🔎 Replaced educational section heading: '{original}' -> '{section['heading']}'")
        for p_idx, para in enumerate(section.get('paragraphs', [])):
            if not isinstance(para, dict):
                continue
            if _looks_educational_title(para.get('subtitle', '')) or _looks_placeholder_title(para.get('subtitle', '')):
                original = para.get('subtitle', '')
                para['subtitle'] = f"{section.get('heading', topic)}의 장면 {p_idx + 1}"
                print(f"🔎 Replaced educational paragraph subtitle: '{original}' -> '{para['subtitle']}'")
    return result_json


def _topic_thumbnail_query(topic: str) -> str:
    if is_mostly_english(topic):
        return topic
    try:
        query = llm_client.generate_text(
            "You create concise English image search queries.",
            f"""
            Translate this magazine topic into one concrete English visual search query.
            Topic: {topic}

            Rules:
            - Return only 2 to 5 English words.
            - Include the exact main subject, dish, object, place, or product.
            - Do not use abstract words like history, trend, concept, modern, vibe.
            - For food topics, include the dish name itself.
            """
        )
        words = re.findall(r"[A-Za-z][A-Za-z0-9'-]*", query or "")
        if len(words) >= 2:
            return " ".join(words[:5]).lower()
    except Exception as e:
        print(f"Topic thumbnail query translation failed: {e}")
    return _fallback_image_keyword([], topic, "")


def _sync_section_thumbnails_from_paragraphs(result_json: dict, overwrite: bool = False) -> dict:
    for section in result_json.get('sections', []) if isinstance(result_json, dict) else []:
        if not isinstance(section, dict):
            continue
        if not overwrite and isinstance(section.get('thumbnail_url'), str) and section['thumbnail_url'].startswith('http'):
            continue
        for para in section.get('paragraphs', []):
            image_url = para.get('image_url') if isinstance(para, dict) else None
            if isinstance(image_url, str) and image_url.startswith('http'):
                section['thumbnail_url'] = image_url
                break
    return result_json


def _normalize_magazine_contract(result_json: dict, topic: str) -> dict:
    """Clean fields the frontend no longer uses and fill safe fallbacks."""
    result_json.pop('subtitle', None)
    result_json.pop('introduction', None)
    result_json = _sanitize_editorial_titles(result_json, topic)

    tags = _normalize_topic_tags(result_json.get('tags', []), topic, result_json)
    result_json['tags'] = tags
    for section in result_json.get('sections', []):
        section.pop('layout_type', None)
        section.pop('layout_hint', None)
        heading = section.get('heading', '')
        for para in section.get('paragraphs', []):
            para['text'] = _strip_source_markers(para.get('text', ''))
            if not para.get('image_search_keyword'):
                para['image_search_keyword'] = _fallback_image_keyword(tags, topic, heading)
    return result_json


def _repair_reasons(result_json: dict) -> list:
    reasons = set()
    if not isinstance(result_json, dict):
        return ["invalid_json_schema"]

    if not result_json.get('title') or not isinstance(result_json.get('title'), str):
        reasons.add("missing_required_field:title")
    elif _looks_placeholder_title(result_json.get('title')):
        reasons.add("placeholder_title")
    if not result_json.get('tags') or not isinstance(result_json.get('tags'), list):
        reasons.add("missing_required_field:tags")

    sections = result_json.get('sections')
    if not isinstance(sections, list):
        reasons.add("invalid_json_schema")
        return sorted(reasons)
    if len(sections) != 2:
        reasons.add("section_count_mismatch")

    normalized_headings = [
        re.sub(r"\s+", " ", str(section.get("heading") or "")).strip().lower()
        for section in sections
        if isinstance(section, dict)
    ]
    if len(normalized_headings) != len(set(normalized_headings)):
        reasons.add("duplicate_section_heading")

    for s_idx, section in enumerate(sections):
        if not isinstance(section, dict):
            reasons.add("invalid_json_schema")
            continue
        if not section.get('heading'):
            reasons.add(f"missing_required_field:section[{s_idx}].heading")
        elif _looks_placeholder_title(section.get('heading')):
            reasons.add("placeholder_heading")
        paragraphs = section.get('paragraphs')
        if not isinstance(paragraphs, list):
            reasons.add("invalid_json_schema")
            continue
        if len(paragraphs) != 3:
            reasons.add("paragraph_count_mismatch")
        if 'layout_type' in section or 'layout_hint' in section:
            reasons.add("forbidden_field_present")
        for p_idx, para in enumerate(paragraphs):
            if not isinstance(para, dict):
                reasons.add("invalid_json_schema")
                continue
            for field in ("subtitle", "text"):
                if not para.get(field):
                    reasons.add(f"missing_required_field:section[{s_idx}].paragraph[{p_idx}].{field}")
            if _looks_placeholder_title(para.get("subtitle")):
                reasons.add("placeholder_subtitle")
            if not para.get('source_url'):
                reasons.add("missing_source_url")
            if not para.get('image_search_keyword'):
                reasons.add("missing_required_field:image_search_keyword")
            if 'image_url' not in para:
                reasons.add("missing_image_url")
            if _paragraph_length(para.get('text')) < PARAGRAPH_MIN_CHARS:
                reasons.add("paragraph_too_short")
    return sorted(reasons)


def _short_paragraphs(result_json: dict, min_chars: int = PARAGRAPH_MIN_CHARS) -> list:
    short_items = []
    if not isinstance(result_json, dict):
        return short_items
    for s_idx, section in enumerate(result_json.get('sections', [])):
        for p_idx, para in enumerate(section.get('paragraphs', [])):
            text = para.get('text') or ''
            length = _paragraph_length(text)
            if length < min_chars:
                short_items.append({
                    "section": s_idx,
                    "paragraph": p_idx,
                    "length": length,
                    "min": min_chars,
                })
    return short_items


def _paragraphs_over_limit(result_json: dict, max_chars: int = PARAGRAPH_MAX_CHARS) -> list:
    over_items = []
    if not isinstance(result_json, dict):
        return over_items
    for s_idx, section in enumerate(result_json.get('sections', [])):
        for p_idx, para in enumerate(section.get('paragraphs', [])):
            text = para.get('text') or ''
            length = _paragraph_length(text)
            if length > max_chars:
                over_items.append({
                    "section": s_idx,
                    "paragraph": p_idx,
                    "length": length,
                    "max": max_chars,
                })
    return over_items


def _trim_to_sentence_limit(text: str, max_chars: int = PARAGRAPH_MAX_CHARS) -> str:
    if not text or _paragraph_length(text) <= max_chars:
        return text
    sentences = re.split(r'(?<=[.!?。！？다요죠음함됨임])\s+', text.strip())
    kept = []
    for sentence in sentences:
        candidate = " ".join(kept + [sentence]).strip()
        if _paragraph_length(candidate) > max_chars:
            break
        kept.append(sentence)
    trimmed = " ".join(kept).strip()
    if trimmed and _paragraph_length(trimmed) >= PARAGRAPH_MIN_CHARS:
        return trimmed
    return text


def _needs_contract_repair(result_json: dict, reasons: list = None) -> bool:
    reasons = reasons if reasons is not None else _repair_reasons(result_json)
    for reason in reasons:
        if (
            reason in STRUCTURAL_REPAIR_REASONS
            or reason.startswith("missing_required_field")
            or reason.startswith("placeholder_")
            or reason == "duplicate_section_heading"
        ):
            if reason in ("missing_required_field:title", "missing_required_field:tags", "missing_required_field:image_search_keyword"):
                continue
            return True
    return False


def _fallback_source_url(labeled_sources: list, search_results: list, section_idx: int, paragraph_idx: int) -> str:
    source_count = len(labeled_sources or [])
    section_source_start = section_idx * 2
    fallback_idx = section_source_start + (paragraph_idx % 2)
    if fallback_idx < source_count:
        return labeled_sources[fallback_idx][0]
    if source_count > 0:
        return labeled_sources[0][0]
    if search_results:
        return search_results[min(paragraph_idx, len(search_results) - 1)].get('url', '')
    return ""


def _apply_local_contract_fixes(result_json: dict, topic: str, labeled_sources: list, search_results: list) -> dict:
    """Fix cheap schema gaps before spending another LLM call on repair."""
    if not isinstance(result_json, dict):
        return result_json
    if not result_json.get('title'):
        result_json['title'] = topic[:22]
    if not result_json.get('tags') or not isinstance(result_json.get('tags'), list):
        result_json['tags'] = ["LIFESTYLE", "TREND"]
    if 'cover_image_url' not in result_json:
        result_json['cover_image_url'] = None

    sections = result_json.get('sections')
    if not isinstance(sections, list):
        return result_json
    if len(sections) > 2:
        result_json['sections'] = sections[:2]

    for s_idx, section in enumerate(result_json.get('sections', [])):
        if not isinstance(section, dict):
            continue
        if not section.get('heading'):
            section['heading'] = f"{topic} 관점 {s_idx + 1}"
        if 'thumbnail_url' not in section:
            section['thumbnail_url'] = None
        section['display_order'] = s_idx
        paragraphs = section.get('paragraphs')
        if not isinstance(paragraphs, list):
            continue
        if len(paragraphs) > 3:
            section['paragraphs'] = paragraphs[:3]
        for p_idx, para in enumerate(section.get('paragraphs', [])):
            if not isinstance(para, dict):
                continue
            if not para.get('source_url'):
                para['source_url'] = _fallback_source_url(labeled_sources, search_results, s_idx, p_idx)
            if not para.get('image_search_keyword'):
                para['image_search_keyword'] = _fallback_image_keyword(result_json.get('tags', []), topic, section.get('heading', ''))
            if 'image_url' not in para:
                para['image_url'] = None
    return result_json


def _fill_missing_final_images(result_json: dict, fallback_image_url: str) -> dict:
    """Keep missing final images as null instead of copying fallback images."""
    if not isinstance(result_json, dict):
        return result_json
    for section in result_json.get('sections', []):
        for para in section.get('paragraphs', []):
            if not para.get('image_url'):
                para['image_url'] = None
        if not section.get('thumbnail_url'):
            section['thumbnail_url'] = None
    return result_json


def _ensure_create_magazine_contract(result_json: dict, topic: str, errors: list = None) -> dict:
    """Ensure Spring-facing create_magazine fields are present even after partial failures."""
    errors = errors if errors is not None else []
    if not isinstance(result_json, dict):
        result_json = {}
    plan = _normalize_magazine_plan({}, topic, result_json)
    result_json["title"] = result_json.get("title") or plan["title"]
    result_json["cover_image_url"] = result_json.get("cover_image_url") if result_json.get("cover_image_url") else None
    tags = result_json.get("tags")
    if not isinstance(tags, list) or not tags:
        result_json["tags"] = plan["tags"]
    else:
        result_json["tags"] = _normalize_topic_tags(tags, topic, result_json)

    sections = result_json.get("sections")
    if not isinstance(sections, list):
        sections = []
    for s_idx in range(2):
        if s_idx >= len(sections) or not isinstance(sections[s_idx], dict):
            sections.append({"heading": plan["section_headings"][min(s_idx, len(plan["section_headings"]) - 1)], "paragraphs": []})
        section = sections[s_idx]
        section["heading"] = section.get("heading") or plan["section_headings"][min(s_idx, len(plan["section_headings"]) - 1)]
        section["thumbnail_url"] = section.get("thumbnail_url") if section.get("thumbnail_url") else None
        section["display_order"] = section.get("display_order", s_idx)
        paragraphs = section.get("paragraphs")
        if not isinstance(paragraphs, list):
            paragraphs = []
        for p_idx in range(3):
            if p_idx >= len(paragraphs) or not isinstance(paragraphs[p_idx], dict):
                paragraphs.append({})
            para = paragraphs[p_idx]
            para["subtitle"] = para.get("subtitle") or f"{section['heading']}의 장면 {p_idx + 1}"
            para["text"] = para.get("text") or "검증 가능한 생성 자료가 부족해 본문 생성을 완료하지 못했습니다."
            para["image_url"] = para.get("image_url") if para.get("image_url") else None
            para["source_url"] = para.get("source_url") or ""
            para["image_search_keyword"] = para.get("image_search_keyword") or " ".join(plan["visual_keywords"][:4])
        section["paragraphs"] = paragraphs[:3]
    result_json["sections"] = sections[:2]

    moodboard = result_json.get("moodboard")
    if not isinstance(moodboard, dict):
        error_type = "MOODBOARD_GENERATION_FAILED" if any("moodboard" in str(error).lower() for error in errors) else "MOODBOARD_MISSING"
        moodboard = {
            "image_url": None,
            "description": "",
            "success": False,
            "status": "FAILED",
            "error_type": error_type,
            "fallback_url": None,
        }
    else:
        moodboard["image_url"] = moodboard.get("image_url") if moodboard.get("image_url") else None
        moodboard["description"] = moodboard.get("description") or ""
        moodboard["fallback_url"] = moodboard.get("fallback_url") if moodboard.get("fallback_url") else None
        if moodboard.get("image_url") is None:
            moodboard["success"] = False
            moodboard["status"] = moodboard.get("status") or "FAILED"
            moodboard["error_type"] = moodboard.get("error_type") or "MOODBOARD_GENERATION_FAILED"
    result_json["moodboard"] = moodboard
    if moodboard.get("image_url") is None:
        result_json["success"] = False
        result_json["error_type"] = moodboard.get("error_type") or "MOODBOARD_GENERATION_FAILED"
    return result_json


def _image_dedupe_key(image) -> str:
    return pexels_dedupe_key(image)


def _image_url_from_candidate(image) -> str:
    if isinstance(image, dict):
        return image.get("url") or ""
    return str(image or "")


def _is_low_resolution_url(url: str) -> bool:
    url_lower = (url or "").lower()
    parsed = urlparse(url_lower)
    low_res_path_tokens = ("tiny", "small", "thumbnail", "thumb")
    path_parts = [part for part in re.split(r"[/_.-]+", parsed.path) if part]
    if any(part in low_res_path_tokens for part in path_parts):
        return True
    params = parse_qs(parsed.query)
    widths = params.get("w", []) + params.get("width", [])
    heights = params.get("h", []) + params.get("height", [])
    for width in widths:
        if width.isdigit() and int(width) < 900:
            return True
    for height in heights:
        if height.isdigit() and int(height) < 600:
            return True
    return bool(re.search(r"[/_-](?:1[0-9]{2}|[1-8][0-9])x(?:1[0-9]{2}|[1-5][0-9]{2}|[1-9][0-9])\b", url_lower))


def _is_pexels_url(url: str) -> bool:
    return "images.pexels.com" in (url or "").lower()


def _iter_image_slots(result_json: dict):
    for section in result_json.get("sections", []) if isinstance(result_json, dict) else []:
        yield section, "thumbnail_url"
        for para in section.get("paragraphs", []) if isinstance(section, dict) else []:
            yield para, "image_url"


def _count_final_images(result_json: dict) -> int:
    count = 1 if result_json.get("cover_image_url") else 0
    for target, field in _iter_image_slots(result_json):
        if target.get(field):
            count += 1
    moodboard = result_json.get("moodboard")
    if isinstance(moodboard, dict) and moodboard.get("image_url"):
        count += 1
    return count


def _count_content_image_slots(result_json: dict) -> int:
    return sum(1 for _target, _field in _iter_image_slots(result_json))


def _count_content_images(result_json: dict) -> int:
    return sum(1 for target, field in _iter_image_slots(result_json) if target.get(field))


def _clear_invalid_final_images(result_json: dict, used_image_keys: set = None) -> dict:
    used_image_keys = used_image_keys if used_image_keys is not None else set()

    def clean(url):
        if not url or not isinstance(url, str) or not url.startswith("http"):
            return None
        if _is_low_resolution_url(url):
            return None
        if not _is_pexels_url(url) and not validate_image_url(url):
            return None
        key = _image_dedupe_key(url)
        if key in used_image_keys:
            return None
        used_image_keys.add(key)
        return url

    result_json["cover_image_url"] = clean(result_json.get("cover_image_url"))
    for target, field in _iter_image_slots(result_json):
        target[field] = clean(target.get(field))
    return result_json


def _ensure_minimum_unique_images(result_json: dict, topic: str, used_image_keys: set, min_images: int = 4) -> dict:
    content_slot_count = _count_content_image_slots(result_json)
    target_content_images = max(0, min(content_slot_count, min_images))
    if _count_content_images(result_json) >= target_content_images:
        return result_json
    queries = []
    topic_query = _topic_thumbnail_query(topic)
    if topic_query:
        queries.append(topic_query)
    for section in result_json.get("sections", []):
        if isinstance(section, dict):
            queries.append(_section_thumbnail_query(topic, section))
            for para in section.get("paragraphs", []):
                if isinstance(para, dict):
                    queries.append(para.get("image_search_keyword"))

    seen_queries = set()
    candidates = []
    for query in queries:
        query = str(query or "").strip()
        normalized = query.lower()
        if not query or normalized in seen_queries:
            continue
        seen_queries.add(normalized)
        try:
            candidates.extend(search_with_pexels_metadata(query, orientation="landscape", per_page=5))
        except Exception as e:
            print(f"Pexels supplement failed for '{query}': {type(e).__name__}: {e}")

    candidate_index = 0

    def next_url():
        nonlocal candidate_index
        while candidate_index < len(candidates):
            candidate = candidates[candidate_index]
            candidate_index += 1
            url = _image_url_from_candidate(candidate)
            key = _image_dedupe_key(candidate)
            if (
                url
                and url.startswith("http")
                and not _is_low_resolution_url(url)
                and key not in used_image_keys
                and (_is_pexels_url(url) or validate_image_url(url))
            ):
                used_image_keys.add(key)
                return url
        return None

    for target, field in _iter_image_slots(result_json):
        if _count_content_images(result_json) >= target_content_images:
            break
        if not target.get(field):
            target[field] = next_url()
    if not result_json.get("cover_image_url"):
        result_json["cover_image_url"] = next_url()
    return result_json


def _dedupe_and_pad_paragraph_texts(result_json: dict, topic: str) -> dict:
    seen = set()
    for s_idx, section in enumerate(result_json.get("sections", [])):
        heading = section.get("heading", topic)
        for p_idx, para in enumerate(section.get("paragraphs", [])):
            text = str(para.get("text") or "").strip()
            normalized = re.sub(r"\s+", " ", text)
            if normalized in seen:
                para["subtitle"] = f"{heading}의 다른 관점 {p_idx + 1}"
                text = (
                    f"{heading}을 다른 각도에서 바라보면, {topic}의 표정은 놓이는 장소와 시간대에 따라 달라진다. "
                    "같은 정보라도 어떤 물성, 색감, 거리감과 함께 놓이느냐에 따라 독자가 받아들이는 밀도는 달라진다. "
                    "이 문단은 앞선 내용과 겹치지 않도록 장면의 배경과 세부 요소를 다시 배열한다. "
                    "마지막에는 독자가 화면을 닫은 뒤에도 떠올릴 수 있는 하나의 촉감과 분위기를 남긴다."
                )
            if _paragraph_length(text) < PARAGRAPH_MIN_CHARS:
                text = (
                    text
                    + " "
                    + f"이 관점은 {topic}를 손에 잡히는 장면으로 좁힐 때 더 선명해진다. "
                    + f"{heading} 안에서 {p_idx + 1}번째 장면은 표면의 질감, 빛의 방향, 주변 사물의 간격이 함께 보일 때 살아난다. "
                    + "독자는 그 구체성 속에서 기사 전체의 분위기를 자연스럽게 따라갈 수 있다."
                )
            while _paragraph_length(text) < PARAGRAPH_MIN_CHARS:
                text += (
                    " 또한 사물의 위치와 색의 온도를 조금 더 분명히 적어두면, "
                    "문장은 정보 전달을 넘어 한 장의 매거진 컷처럼 오래 남는다."
                )
            padded_normalized = re.sub(r"\s+", " ", text).strip()
            if padded_normalized in seen:
                text = (
                    f"{heading}을 또 다른 순서로 바라보면, {topic}는 결과보다 장면의 첫인상으로 먼저 다가온다. "
                    "동일한 정보가 반복될 때 독자는 금방 피로해지므로, 이 문단은 앞선 내용과 달리 색, 표면, 거리, 계절감을 중심에 둔다. "
                    "작은 사물이 놓인 방향과 주변의 여백을 함께 묘사하면 문장의 화면성이 살아난다. "
                    "그렇게 정리된 문단은 설명보다 이미지에 가까운 리듬으로 매거진의 톤을 붙든다."
                )
                while _paragraph_length(text) < PARAGRAPH_MIN_CHARS:
                    text += (
                        " 특히 마지막 문장은 단정한 결론보다 잔상에 가깝게 남아야 하며, "
                        "그 여백이 다음 섹션으로 넘어가는 호흡을 만든다."
                    )
            para["text"] = _trim_to_sentence_limit(text)
            seen.add(re.sub(r"\s+", " ", para["text"]).strip())
    return result_json


def _repair_magazine_contract(result_json: dict, topic: str, labeled_material: str) -> dict:
    repair_prompt = f"""
    아래 매거진 JSON은 구조는 대체로 맞지만 일부 문단이 너무 짧거나 필수 필드가 약할 수 있다.
    완성본 JSON으로 수리하라.

    [Topic]
    {topic}

    [Research Material]
    {labeled_material}

    [Current JSON]
    {json.dumps(result_json, ensure_ascii=False)}

    [Repair Rules]
    - 유효한 JSON 객체만 반환한다. 코드블럭과 설명은 금지한다.
    - 최상위 필드는 `title`, `tags`, `sections`, `cover_image_url`만 유지한다.
    - 정확히 2개 섹션, 각 섹션 정확히 3개 문단을 유지한다.
    - 섹션에 `layout_type`, `layout_hint`를 넣지 않는다.
    - 각 문단의 `text`는 반드시 한국어 250~550자로 확장한다.
    - 전체 톤은 교육 자료가 아니라 프리미엄 한국어 매거진 산문이어야 한다.
    - "개념", "개념 설명", "개념 다지기", "이점", "장점", "효과", "환경 이점", "실전", "실전 워크플로우", "워크플로우", "실천 방법", "기대 효과", "핵심 포인트", "활용법", "추천 기준", "가이드", "방법론" 같은 교육용/커리큘럼식 표현을 `heading`, `subtitle`, `text` 어디에서도 구조 표지로 쓰지 않는다.
    - 문단은 도식적 설명 순서가 아니라 장면 관찰, 구체 정보, 맥락 해석, 감각적 잔상을 자연스럽게 엮어 쓴다.
    - 각 문단의 `text` 안에는 URL이나 `[source_url]:` 표기를 넣지 않는다.
    - 기존 `source_url`과 `image_search_keyword`는 최대한 보존한다.
    - `source_url`과 `image_search_keyword`가 비어 있으면 채운다.
    - 사실은 Research Material과 Current JSON의 범위 안에서만 보강한다.
    """
    try:
        repaired = llm_client.generate_json(
            "You are a strict JSON repair engine for a Korean magazine. Output valid JSON only.",
            repair_prompt,
            temperature=0.4
        )
        return repaired if isinstance(repaired, dict) else result_json
    except Exception as e:
        print(f"⚠️ Magazine contract repair failed: {e}")
        return result_json


def _apply_targeted_expansion_items(result_json: dict, expanded: list) -> dict:
    if not isinstance(expanded, list):
        return result_json
    for item in expanded:
        if not isinstance(item, dict):
            continue
        s_idx = item.get("section")
        p_idx = item.get("paragraph")
        text = item.get("text")
        if not isinstance(s_idx, int) or not isinstance(p_idx, int) or not text:
            continue
        text = _trim_to_sentence_limit(text)
        try:
            result_json['sections'][s_idx]['paragraphs'][p_idx]['text'] = text
        except (IndexError, KeyError, TypeError):
            continue
    return result_json


def _expand_short_paragraphs(
    result_json: dict,
    topic: str,
    labeled_material: str,
    short_items: list = None,
    max_attempts: int = 1,
) -> dict:
    short_items = short_items if short_items is not None else _short_paragraphs(result_json)
    short_items = sorted(short_items, key=lambda item: item.get("length", 0))[:TARGETED_EXPANSION_MAX_ITEMS]
    if not short_items:
        return result_json

    attempts = 0
    while short_items and attempts < max_attempts:
        attempts += 1
        targets = []
        for item in short_items:
            section = result_json.get('sections', [])[item["section"]]
            para = section.get('paragraphs', [])[item["paragraph"]]
            targets.append({
                **item,
                "section_heading": section.get('heading', ''),
                "subtitle": para.get('subtitle', ''),
                "source_url": para.get('source_url', ''),
                "current_text": para.get('text', ''),
            })

        expand_prompt = f"""
        아래의 짧은 문단들만 프리미엄 한국어 매거진 문체로 확장하라.
        전체 매거진 구조, 섹션 수, 문단 수, subtitle, source_url, image_search_keyword, image_url은 절대 변경하지 않는다.

        [Topic]
        {topic}

        [Research Material]
        {labeled_material}

        [Short Paragraph Targets]
        {json.dumps(targets, ensure_ascii=False)}

        [Rules]
        - 유효한 JSON 배열만 반환한다. 설명과 코드블럭은 금지한다.
        - 배열의 각 객체는 `section`, `paragraph`, `text`만 가진다.
        - 입력된 target 개수와 같은 개수의 객체를 반환한다.
        - 각 `text`는 한국어 {PARAGRAPH_MIN_CHARS}~{PARAGRAPH_MAX_CHARS}자로 작성한다.
        - 각 `text`는 최소 5문장 이상으로 구성한다.
        - 기존 문장의 관점은 유지하되, 배경 맥락, 구체적인 장면, 독자 관점의 해석, 감각적/공간적 묘사를 보강한다.
        - "개념", "실전", "워크플로우", "실천 방법", "기대 효과", "핵심 포인트", "활용법" 같은 교육용/커리큘럼식 표현을 구조 표지로 쓰지 않는다.
        - 각 `text` 안에 URL, `[source_url]:`, 출처 표기 문장을 넣지 않는다.
        - Markdown 강조, 인용, 목록은 쓰지 않는다. 문단형 산문으로만 작성한다.
        """
        try:
            expanded = llm_client.generate_json(
                "You expand only selected short Korean magazine paragraph texts. Output a valid JSON array only.",
                expand_prompt,
                temperature=0.45
            )
            result_json = _apply_targeted_expansion_items(result_json, expanded)
            target_positions = {(item["section"], item["paragraph"]) for item in short_items}
            over_limit = [
                item for item in _paragraphs_over_limit(result_json)
                if (item["section"], item["paragraph"]) in target_positions
            ]
            if over_limit:
                print(f"🔎 Trimming overlong targeted expansion paragraphs by sentence: {over_limit}")
                for item in over_limit:
                    para = result_json['sections'][item["section"]]['paragraphs'][item["paragraph"]]
                    para['text'] = _trim_to_sentence_limit(para.get('text', ''))
            short_items = [
                item for item in _short_paragraphs(result_json)
                if (item["section"], item["paragraph"]) in target_positions
            ]
        except Exception as e:
            print(f"⚠️ Targeted paragraph expansion failed: {e}")
            break
    return result_json

def _log_create_timing(request_id: str, timings: dict, result_json: dict, errors: list, skipped_steps: list):
    sections = result_json.get('sections', []) if isinstance(result_json, dict) else []
    paragraph_counts = [len(section.get('paragraphs', [])) for section in sections]
    moodboard = result_json.get('moodboard') if isinstance(result_json, dict) else None
    summary = {
        **timings,
        "sections_count": len(sections),
        "paragraph_counts": paragraph_counts,
        "has_moodboard": bool(moodboard),
        "moodboard_image_url_present": bool(moodboard and moodboard.get('image_url')),
        "errors": errors,
        "skipped_steps": skipped_steps,
    }
    print(f"[create_magazine][request_id={request_id}] timing: {json.dumps(summary, ensure_ascii=False)}")


def _log_create_step(request_id: str, step: str, elapsed: float, total_start: float, **extra):
    payload = {
        "step": step,
        "elapsed": round(elapsed, 3),
        "total_elapsed": round(time.perf_counter() - total_start, 3),
        **extra,
    }
    print(f"[create_magazine][request_id={request_id}] step_timing: {json.dumps(payload, ensure_ascii=False)}")


def generate_magazine_content(topic: str, user_interests: list = None, user_mood: str = None, request_id: str = None, runpod_handler_start_time: float = 0):
    request_id = request_id or str(uuid.uuid4())[:8]
    total_start = time.perf_counter()
    timings = {
        "request_received_time": 0,
        "git_commit": _runtime_commit(),
        "paragraph_min_chars": PARAGRAPH_MIN_CHARS,
        "paragraph_max_chars": PARAGRAPH_MAX_CHARS,
        "runpod_handler_start_time": round(runpod_handler_start_time, 3),
        "paragraph_image_download_time": 0,
        "s3_upload_time": 0,
        "moodboard_upload_time": 0,
        "spring_callback_enabled": False,
        "spring_callback_attempted": False,
        "spring_callback_time": 0,
        "spring_callback_success": False,
        "spring_callback_error": "",
        "spring_callback_payload_bytes": 0,
        "spring_callback_payload_had_base64": False,
        "jina_auth_disabled_for_request": False,
        "jina_auth_failure_count": 0,
        "jina_timeout_count": 0,
        "jina_urls_attempted": 0,
        "jina_urls_succeeded": 0,
        "jina_urls_failed": 0,
        "scraping_total_time": 0,
        "jina_total_time": 0,
        "search_total_time": 0,
        "llm_total_time": 0,
        "image_fetch_time": 0,
        "moodboard_total_time": 0,
        "callback_response_time": 0,
        "contract_repair_needed": False,
        "contract_repair_reason": [],
        "contract_repair_time": 0,
        "targeted_expansion_needed": False,
        "targeted_expansion_reason": [],
        "targeted_expansion_time": 0,
        "targeted_expansion_count": 0,
        "initial_generation_time": 0,
        "paragraph_length_metric": PARAGRAPH_LENGTH_METRIC,
        "initial_paragraph_lengths": [],
        "openai_call_count": 0,
        "final_section_count": 0,
        "final_paragraph_counts": [],
        "short_paragraphs": [],
        "targeted_expansion_items": [],
        "remaining_short_paragraphs": [],
        "short_paragraphs_after_expansion": [],
    }
    errors = []
    skipped_steps = []
    print(f"[create_magazine][request_id={request_id}] Magazine Editor started for: {topic}")
    print(
        f"[create_magazine][request_id={request_id}] runtime: "
        f"git_commit={_runtime_commit()} "
        f"paragraph_min_chars={PARAGRAPH_MIN_CHARS} "
        f"paragraph_max_chars={PARAGRAPH_MAX_CHARS} "
        f"paragraph_length_policy={PARAGRAPH_MIN_CHARS}-{PARAGRAPH_MAX_CHARS}"
    )
    
    # [Language Guard] Translate English topic to Korean to set the "Korean Persona" early
    original_topic = topic
    if is_mostly_english(topic):
        translation_start = time.perf_counter()
        korean_topic = translate_to_korean(topic, "magazine topic")
        timings["topic_translation_time"] = round(time.perf_counter() - translation_start, 3)
        print(f"  -> Input translation: {original_topic} -> {korean_topic}")
        topic = korean_topic
    else:
        timings["topic_translation_time"] = 0

    # 1. Context building
    interest_context = ""
    if user_interests and len(user_interests) > 0:
        interests_str = ', '.join(user_interests)
        interest_context = f"[Reader Profile]\nThis reader is interested in: {interests_str}\n"

    moodboard_executor = None
    moodboard_future = None
    timings["moodboard_submit_time"] = 0

    # Search with original (if English) + Korean for maximum relevance
    search_query = f"{original_topic} {topic}" if original_topic != topic else topic
    web_search_start = time.perf_counter()
    search_results, images = search_with_tavily(search_query, topic=topic)
    search_results = _filter_research_results(search_results)
    timings["web_search_time"] = round(time.perf_counter() - web_search_start, 3)
    _log_create_step(
        request_id,
        "search.tavily",
        timings["web_search_time"],
        total_start,
        results_count=len(search_results or []),
        images_count=len(images or []),
    )
    
    # 2. [Parallel Scraping V2] Labeled source scraping
    # Initial magazines use 2 sections x 3 paragraphs. We try 4 Jina sources
    # so each section can be grounded by two deeper reads.
    labeled_sources = []
    scraped_images = []
    jina_state = {
        "auth_disabled": False,
        "auth_failure_count": 0,
        "timeout_count": 0,
        "urls_attempted": 0,
        "urls_succeeded": 0,
        "urls_failed": 0,
    }
    if search_results:
        jina_max_urls = int(os.getenv("JINA_MAX_URLS", "3"))
        urls = [r['url'] for r in search_results[:jina_max_urls]]
        scrape_start = time.perf_counter()
        labeled_sources, scraped_images = scrape_labeled_sources(urls, max_count=jina_max_urls, request_state=jina_state)
        timings["jina_scrape_time"] = round(time.perf_counter() - scrape_start, 3)
        timings["jina_total_time"] = timings["jina_scrape_time"]
        timings["jina_auth_disabled_for_request"] = bool(jina_state.get("auth_disabled"))
        timings["jina_auth_failure_count"] = jina_state.get("auth_failure_count", 0)
        timings["jina_timeout_count"] = jina_state.get("timeout_count", 0)
        timings["jina_urls_attempted"] = jina_state.get("urls_attempted", 0)
        timings["jina_urls_succeeded"] = jina_state.get("urls_succeeded", 0)
        timings["jina_urls_failed"] = jina_state.get("urls_failed", 0)
        
        if not labeled_sources and search_results:
            for r in search_results[:4]:
                labeled_sources.append((r.get('url', ''), r.get('content', '')))
            skipped_steps.append("jina_all_failed_used_tavily_snippets")
        
        validation_start = time.perf_counter()
        scraped_images = [img for img in scraped_images if validate_image_url(img)]
        timings["scraped_image_validation_time"] = round(time.perf_counter() - validation_start, 3)
        timings["scraping_total_time"] = round(timings["jina_scrape_time"] + timings["scraped_image_validation_time"], 3)
        _log_create_step(
            request_id,
            "search.scraping",
            timings["scraping_total_time"],
            total_start,
            jina_total_time=timings["jina_total_time"],
            image_validation_time=timings["scraped_image_validation_time"],
            sources_count=len(labeled_sources),
            scraped_images_count=len(scraped_images),
            jina_urls_attempted=timings["jina_urls_attempted"],
            jina_urls_succeeded=timings["jina_urls_succeeded"],
            jina_timeout_count=timings["jina_timeout_count"],
        )
    else:
        timings["jina_scrape_time"] = 0
        timings["jina_total_time"] = 0
        timings["scraped_image_validation_time"] = 0
        timings["scraping_total_time"] = 0
        skipped_steps.append("no_search_results_for_jina")
        _log_create_step(request_id, "search.scraping", 0, total_start, skipped=True, reason="no_search_results")
    timings["search_total_time"] = round(timings["web_search_time"] + timings["scraping_total_time"], 3)

    # 3. Build labeled research material
    labeled_material = ""
    for i, (url, content) in enumerate(labeled_sources):
        truncated = content[:2000] if content else "No content available."
        labeled_material += f"\n[Source {i+1}: {url}]\n{truncated}\n"
    
    if not labeled_material.strip():
        if _requires_verified_sources(topic) or _requires_verified_sources(original_topic):
            if moodboard_executor:
                moodboard_executor.shutdown(wait=False, cancel_futures=True)
            return {
                "error": "INSUFFICIENT_VERIFIED_SOURCES",
                "message": "검증 가능한 검색 결과가 없어 구체적인 추천 대상을 생성하지 않았습니다.",
            }
        labeled_material = "No research material available. Use non-specific general editorial guidance only. Do not name people, creators, brands, places, channels, accounts, products, prices, dates, rankings, or statistics."

    from app.core.moodboard_maker import generate_moodboard
    moodboard_seed_tags = _moodboard_seed_keywords(topic, search_results, labeled_sources)
    moodboard_executor = ThreadPoolExecutor(max_workers=1)
    moodboard_submit_start = time.perf_counter()
    moodboard_future = moodboard_executor.submit(
        generate_moodboard,
        topic=topic,
        user_interests=user_interests,
        magazine_tags=moodboard_seed_tags,
        magazine_titles=[topic, *moodboard_seed_tags[:4]],
        user_mood=user_mood,
        request_id=request_id,
    )
    timings["moodboard_submit_time"] = round(time.perf_counter() - moodboard_submit_start, 3)
    _log_create_step(
        request_id,
        "moodboard.submit",
        timings["moodboard_submit_time"],
        total_start,
        seed_tags=moodboard_seed_tags[:5],
    )

    system_prompt = MAGAZINE_SYSTEM_PROMPT_V8
    user_prompt = f"""
    Topic (Korean): {topic}
    Original Topic (if any): {original_topic}
    {interest_context}
    [Research Material - LABELED SOURCES]
    {labeled_material}
    [Available Images]
    {json.dumps(images, ensure_ascii=False)}
    
    [ABSOLUTE LANGUAGE RULE]
    - YOU MUST RESPOND IN KOREAN (HANGUL).
    - Even if the sources are in English, translate them into professional Korean.
    - Title, Headings, and Body Text must all be in Korean.
    """

    print(f"AI Crafting V8 magazine (Source-grounded Korean Editor)...")
    llm_call_count_start = getattr(llm_client, "call_count", 0)
    content_start = time.perf_counter()
    result_json = llm_client.generate_json(
        system_prompt,
        user_prompt,
        temperature=0.7,
        response_format=MAGAZINE_RESPONSE_FORMAT,
    )
    timings["content_generation_time"] = round(time.perf_counter() - content_start, 3)
    timings["initial_generation_time"] = timings["content_generation_time"]
    timings["llm_total_time"] = timings["content_generation_time"]
    _log_create_step(
        request_id,
        "llm.initial_generation",
        timings["content_generation_time"],
        total_start,
        openai_call_count_delta=getattr(llm_client, "call_count", 0) - llm_call_count_start,
    )
    
    # Handle Safety/NSFW Errors
    if "error" in result_json:
        print(f"⚠️ AI Server Policy Triggered: {result_json.get('error')}")
        errors.append(f"content_error:{result_json.get('error')}")
        if moodboard_executor:
            moodboard_executor.shutdown(wait=False, cancel_futures=True)
        timings["total_time"] = round(time.perf_counter() - total_start, 3)
        timings["total_generation_time"] = timings["total_time"]
        _log_create_timing(request_id, timings, result_json, errors, skipped_steps)
        return result_json

    if result_json.get('thought_process'):
        del result_json['thought_process']
    
    # [Final Language Guard] If the LLM still returns English, force translate the whole object
    result_json = force_translate_magazine_json(result_json)
    result_json = _normalize_magazine_contract(result_json, topic)
    timings["initial_paragraph_lengths"] = _paragraph_lengths(result_json)
    print(
        f"🔎 Initial paragraph lengths ({PARAGRAPH_LENGTH_METRIC}): "
        f"{timings['initial_paragraph_lengths']}"
    )
    pre_fix_reasons = _repair_reasons(result_json)
    if pre_fix_reasons:
        print(f"🔎 Contract check before local fix: {pre_fix_reasons}")
    result_json = _apply_local_contract_fixes(result_json, topic, labeled_sources, search_results)
    result_json = _normalize_magazine_contract(result_json, topic)
    repair_reasons = _repair_reasons(result_json)
    targeted_expansion_reasons = []
    if "paragraph_too_short" in repair_reasons:
        targeted_expansion_reasons.append("paragraph_too_short")
    contract_repair_reasons = [reason for reason in repair_reasons if reason != "paragraph_too_short"]
    repair_needed = _needs_contract_repair(result_json, contract_repair_reasons)
    timings["contract_repair_needed"] = repair_needed
    timings["contract_repair_reason"] = contract_repair_reasons
    timings["targeted_expansion_needed"] = bool(targeted_expansion_reasons)
    timings["targeted_expansion_reason"] = targeted_expansion_reasons
    if repair_reasons:
        print(f"🔎 Contract check after local fix: {repair_reasons}")
    if repair_needed:
        print(f"🛠️ Repairing magazine contract: {repair_reasons}")
        repair_start = time.perf_counter()
        result_json = _repair_magazine_contract(result_json, topic, labeled_material)
        timings["contract_repair_time"] = round(time.perf_counter() - repair_start, 3)
        timings["llm_total_time"] = round(timings["llm_total_time"] + timings["contract_repair_time"], 3)
        _log_create_step(
            request_id,
            "llm.contract_repair",
            timings["contract_repair_time"],
            total_start,
            repair_reasons=repair_reasons,
        )
        result_json = force_translate_magazine_json(result_json)
        result_json = _normalize_magazine_contract(result_json, topic)
        result_json = _apply_local_contract_fixes(result_json, topic, labeled_sources, search_results)
        result_json = _normalize_magazine_contract(result_json, topic)
    else:
        timings["contract_repair_time"] = 0
    
    # 4. Ensure source_url fallback at the paragraph level.
    # For 2-section magazines, map two Jina/Tavily sources per section:
    # section 0 -> sources 0,1,0 / section 1 -> sources 2,3,2.
    source_count = len(labeled_sources)
    for s_idx, section in enumerate(result_json.get('sections', [])):
        for p_idx, para in enumerate(section.get('paragraphs', [])):
            if not para.get('source_url'):
                section_source_start = s_idx * 2
                fallback_idx = section_source_start + (p_idx % 2)
                if fallback_idx < source_count:
                    para['source_url'] = labeled_sources[fallback_idx][0]
                elif source_count > 0:
                    para['source_url'] = labeled_sources[0][0]

    short_before_expansion = _short_paragraphs(result_json)
    expansion_targets = sorted(short_before_expansion, key=lambda item: item["length"])[:TARGETED_EXPANSION_MAX_ITEMS]
    timings["short_paragraphs"] = short_before_expansion
    timings["targeted_expansion_items"] = expansion_targets
    if short_before_expansion:
        print(f"🔎 Short paragraphs below threshold: {short_before_expansion}")
    if expansion_targets:
        print(f"🔎 Short paragraphs targeted for expansion: {expansion_targets}")
    expand_start = time.perf_counter()
    if expansion_targets:
        result_json = _expand_short_paragraphs(result_json, topic, labeled_material, short_items=expansion_targets)
    timings["paragraph_expansion_time"] = round(time.perf_counter() - expand_start, 3)
    timings["targeted_expansion_time"] = timings["paragraph_expansion_time"]
    timings["llm_total_time"] = round(timings["llm_total_time"] + timings["paragraph_expansion_time"], 3)
    timings["targeted_expansion_count"] = len(expansion_targets)
    _log_create_step(
        request_id,
        "llm.targeted_expansion",
        timings["paragraph_expansion_time"],
        total_start,
        targeted_expansion_count=len(expansion_targets),
    )
    result_json = _normalize_magazine_contract(result_json, topic)
    timings["short_paragraphs_after_expansion"] = _short_paragraphs(result_json)
    timings["remaining_short_paragraphs"] = timings["short_paragraphs_after_expansion"]
    if timings["remaining_short_paragraphs"]:
        print(f"🔎 Remaining short paragraphs after capped expansion: {timings['remaining_short_paragraphs']}")

    # 5. Parallel image searching + moodboard generation.
    # Moodboard is already running from search/source-derived keywords, not a
    # hard-coded category palette.
    print(f"Parallelizing image searching and keyword-grounded moodboard generation...")
    
    used_image_keys = set()
    if result_json.get('cover_image_url') and result_json['cover_image_url'].startswith('http'):
        used_image_keys.add(_image_dedupe_key(result_json['cover_image_url']))

    lock = threading.Lock()
    real_tavily_images = [img for img in images]
    indices = {"scraped": 0, "tavily": 0}

    def assign_candidate(target, candidate, validate: bool = True):
        url = _image_url_from_candidate(candidate)
        if not url or not url.startswith('http') or _is_low_resolution_url(url):
            return False
        key = _image_dedupe_key(candidate)
        if key in used_image_keys:
            return False
        if validate and not validate_image_url(url):
            return False
        target['thumbnail_url' if 'thumbnail_url' in target else 'image_url'] = url
        used_image_keys.add(key)
        return True

    def assign_image_to_target(target, query, allow_fallback=True):
        assigned = False
        if query:
            try:
                pexels_imgs = search_with_pexels_metadata(query, orientation='landscape', per_page=5)
                with lock:
                    for img in pexels_imgs:
                        if assign_candidate(target, img, validate=False):
                            assigned = True
                            return True
            except Exception as e:
                print(f"Pexels search failed for '{query}': {type(e).__name__}: {e}")
        if not allow_fallback:
            return False
        with lock:
            if not assigned:
                while indices["scraped"] < len(scraped_images):
                    img = scraped_images[indices["scraped"]]
                    indices["scraped"] += 1
                    if assign_candidate(target, img, validate=False):
                        return True
                while indices["tavily"] < len(real_tavily_images):
                    img = real_tavily_images[indices["tavily"]]
                    indices["tavily"] += 1
                    if assign_candidate(target, img, validate=True):
                        return True
        return False

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        image_search_start = time.perf_counter()
        topic_thumbnail_query = _topic_thumbnail_query(topic)
        for i, section in enumerate(result_json.get('sections', [])):
            section['display_order'] = i
            section['thumbnail_url'] = None
            futures.append(executor.submit(assign_image_to_target, section, topic_thumbnail_query, False))
            for para in section.get('paragraphs', []):
                if not para.get('image_url') or not para['image_url'].startswith('http'):
                    pq = para.get('image_search_keyword', f"{topic} {section.get('heading', '')}")
                    futures.append(executor.submit(assign_image_to_target, para, pq))
        for f in futures:
            try:
                f.result()
            except Exception as e:
                errors.append(f"image_future_exception:{type(e).__name__}:{e}")
                print(f"Image assignment future failed: {type(e).__name__}: {e}")
        result_json = _sync_section_thumbnails_from_paragraphs(result_json)
        timings["paragraph_image_search_time"] = round(time.perf_counter() - image_search_start, 3)
        timings["image_fetch_time"] = timings["paragraph_image_search_time"]
        _log_create_step(
            request_id,
            "image_fetch.paragraph_images",
            timings["paragraph_image_search_time"],
            total_start,
            sections_count=len(result_json.get('sections', [])),
            paragraph_counts=[len(section.get('paragraphs', [])) for section in result_json.get('sections', [])],
        )
        moodboard_wait_start = time.perf_counter()
        try:
            # Do not use a timeout here. If this times out inside the
            # ThreadPoolExecutor context, Python still waits for the running
            # future during executor shutdown, but the moodboard result is
            # discarded. Spring expects create_magazine to include moodboard
            # when generation eventually succeeds.
            moodboard_data = moodboard_future.result() if moodboard_future else None
            timings["moodboard_wait_after_content_time"] = round(time.perf_counter() - moodboard_wait_start, 3)
            if moodboard_data and moodboard_data.get('image_url'):
                result_json['moodboard'] = moodboard_data
                if isinstance(moodboard_data.get("timing"), dict):
                    timings.update(moodboard_data["timing"])
                print(f"Parallel Moodboard attached: {moodboard_data.get('image_url', '')[:40]}")
            else:
                if isinstance(moodboard_data, dict):
                    result_json['moodboard'] = moodboard_data
                errors.append(f"moodboard_no_usable_image:{moodboard_data}")
                print(f"Moodboard generation returned no usable image: {moodboard_data}")
        except Exception as e:
            timings["moodboard_wait_after_content_time"] = round(time.perf_counter() - moodboard_wait_start, 3)
            errors.append(f"moodboard_exception:{type(e).__name__}:{e}")
            print(f"Moodboard parallel generation failed: {type(e).__name__}: {e}")
        finally:
            moodboard_executor.shutdown(wait=True)
        timings["moodboard_total_time"] = round(
            timings.get("moodboard_prompt_generation_time", 0)
            + timings.get("moodboard_image_generation_time", 0)
            + timings.get("moodboard_wait_after_content_time", 0),
            3,
        )
        _log_create_step(
            request_id,
            "moodboard.complete",
            timings["moodboard_total_time"],
            total_start,
            wait_after_content_time=timings.get("moodboard_wait_after_content_time", 0),
            has_moodboard=bool(result_json.get("moodboard") and result_json["moodboard"].get("image_url")),
        )

    assembly_start = time.perf_counter()
    if not result_json.get('cover_image_url') or not result_json['cover_image_url'].startswith('http'):
        with lock:
            for candidate in [*scraped_images, *real_tavily_images, *images]:
                url = _image_url_from_candidate(candidate)
                if url and url.startswith('http') and not _is_low_resolution_url(url) and validate_image_url(url):
                    result_json['cover_image_url'] = url
                    used_image_keys.add(_image_dedupe_key(candidate))
                    break
            else:
                result_json['cover_image_url'] = None
    paragraph_fallback_image = result_json.get('cover_image_url')
    if not paragraph_fallback_image and result_json.get("moodboard"):
        paragraph_fallback_image = result_json["moodboard"].get("image_url")
    result_json = _fill_missing_final_images(result_json, paragraph_fallback_image)
    result_json = _ensure_create_magazine_contract(result_json, topic, errors)
    used_image_keys = set()
    result_json = _clear_invalid_final_images(result_json, used_image_keys)
    result_json = _ensure_minimum_unique_images(
        result_json,
        topic,
        used_image_keys,
        min_images=_count_content_image_slots(result_json),
    )
    result_json = _dedupe_and_pad_paragraph_texts(result_json, topic)
    result_json = _ensure_create_magazine_contract(result_json, topic, errors)
    timings["final_json_assembly_time"] = round(time.perf_counter() - assembly_start, 3)
    timings["callback_response_time"] = timings["final_json_assembly_time"]
    _log_create_step(
        request_id,
        "response.assembly",
        timings["final_json_assembly_time"],
        total_start,
        spring_callback_enabled=timings["spring_callback_enabled"],
        spring_callback_attempted=timings["spring_callback_attempted"],
    )
    timings["total_time"] = round(time.perf_counter() - total_start, 3)
    timings["total_generation_time"] = timings["total_time"]
    timings["openai_call_count"] = getattr(llm_client, "call_count", 0) - llm_call_count_start
    timings["final_section_count"] = len(result_json.get('sections', []))
    timings["final_paragraph_counts"] = [
        len(section.get('paragraphs', [])) for section in result_json.get('sections', [])
    ]

    print(f"V8 Magazine created: 2 sections with parallel research and paragraph-level source tracking")
    _log_create_timing(request_id, timings, result_json, errors, skipped_steps)
    return result_json
