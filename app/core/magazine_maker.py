from app.core.llm_client import llm_client
import json
import re
from app.core.searcher import search_with_tavily, scrape_with_jina, extract_images_from_content, get_topic_fallback_images, scrape_multiple_with_jina, scrape_labeled_sources, validate_image_url, search_with_pexels
from app.core.prompts import MAGAZINE_SYSTEM_PROMPT_V8
from app.core.utils import is_mostly_english, translate_to_korean, force_translate_magazine_json
from concurrent.futures import ThreadPoolExecutor
import threading

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


def _strip_source_markers(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"\n?\s*\[source_url\]:\s*https?://\S+\s*", "", text)
    text = re.sub(r"\n?\s*출처\s*:\s*https?://\S+\s*", "", text)
    return text.strip()


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


def _normalize_magazine_contract(result_json: dict, topic: str) -> dict:
    """Clean fields the frontend no longer uses and fill safe fallbacks."""
    result_json.pop('subtitle', None)
    result_json.pop('introduction', None)

    tags = result_json.get('tags', [])
    for section in result_json.get('sections', []):
        section.pop('layout_type', None)
        section.pop('layout_hint', None)
        heading = section.get('heading', '')
        for para in section.get('paragraphs', []):
            para['text'] = _strip_source_markers(para.get('text', ''))
            if not para.get('image_search_keyword'):
                para['image_search_keyword'] = _fallback_image_keyword(tags, topic, heading)
    return result_json


def _needs_contract_repair(result_json: dict) -> bool:
    if len(result_json.get('sections', [])) != 2:
        return True
    for section in result_json.get('sections', []):
        if len(section.get('paragraphs', [])) != 3:
            return True
        if 'layout_type' in section or 'layout_hint' in section:
            return True
        for para in section.get('paragraphs', []):
            if not para.get('source_url') or not para.get('image_search_keyword'):
                return True
            if len(para.get('text') or '') < 350:
                return True
    return False


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
    - 각 문단의 `text`는 반드시 한국어 350~550자로 확장한다.
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


def _expand_short_paragraphs(result_json: dict, topic: str, labeled_material: str) -> dict:
    for section in result_json.get('sections', []):
        paragraphs = section.get('paragraphs', [])
        if not any(len(para.get('text') or '') < 350 for para in paragraphs):
            continue

        expand_prompt = f"""
        아래 섹션의 문단 본문을 프리미엄 한국어 매거진 문체로 확장하라.

        [Topic]
        {topic}

        [Section Heading]
        {section.get('heading', '')}

        [Research Material]
        {labeled_material}

        [Current Paragraphs]
        {json.dumps(paragraphs, ensure_ascii=False)}

        [Rules]
        - 유효한 JSON 배열만 반환한다. 설명과 코드블럭은 금지한다.
        - 배열 길이는 정확히 3개다.
        - 각 객체의 `subtitle`, `source_url`, `image_search_keyword`, `image_url`은 보존한다.
        - 각 객체의 `text`만 확장한다.
        - 각 `text`는 한국어 350~550자로 작성한다.
        - 각 `text`는 최소 5문장 이상으로 구성한다.
        - 각 `text`에는 배경 맥락, 구체적인 실행 팁, 독자 관점의 해석, 감각적/공간적 묘사를 모두 포함한다.
        - 각 `text` 안에 URL, `[source_url]:`, 출처 표기 문장을 넣지 않는다.
        - Markdown은 `**굵게**`, `> 인용`, `- 목록`을 필요한 만큼 자연스럽게 사용한다.
        """
        try:
            expanded = llm_client.generate_json(
                "You expand short Korean magazine paragraphs. Output a valid JSON array only.",
                expand_prompt,
                temperature=0.5
            )
            if isinstance(expanded, list) and len(expanded) == 3:
                for idx, para in enumerate(expanded):
                    original = paragraphs[idx] if idx < len(paragraphs) else {}
                    if not para.get('source_url') and original.get('source_url'):
                        para['source_url'] = original['source_url']
                    if not para.get('image_search_keyword') and original.get('image_search_keyword'):
                        para['image_search_keyword'] = original['image_search_keyword']
                    if 'image_url' not in para and 'image_url' in original:
                        para['image_url'] = original.get('image_url')
                section['paragraphs'] = expanded
        except Exception as e:
            print(f"⚠️ Paragraph expansion failed for section '{section.get('heading', '')}': {e}")
    return result_json

def generate_magazine_content(topic: str, user_interests: list = None, user_mood: str = None):
    print(f"Magazine Editor started for: {topic}")
    
    # [Language Guard] Translate English topic to Korean to set the "Korean Persona" early
    original_topic = topic
    if is_mostly_english(topic):
        korean_topic = translate_to_korean(topic, "magazine topic")
        print(f"  -> Input translation: {original_topic} -> {korean_topic}")
        topic = korean_topic

    # 1. Context building
    interest_context = ""
    mood_context = ""
    if user_interests and len(user_interests) > 0:
        interests_str = ', '.join(user_interests)
        interest_context = f"[Reader Profile]\nThis reader is interested in: {interests_str}\n"
    
    if user_mood:
        mood_context = f"[User Mood]\nThe user wants a '{user_mood}' style.\n"

    # Search with original (if English) + Korean for maximum relevance
    search_query = f"{original_topic} {topic}" if original_topic != topic else topic
    search_results, images = search_with_tavily(search_query, topic=topic)
    
    # 2. [Parallel Scraping V2] Labeled source scraping
    # Initial magazines use 2 sections x 3 paragraphs. We try 4 Jina sources
    # so each section can be grounded by two deeper reads.
    labeled_sources = []
    scraped_images = []
    if search_results:
        urls = [r['url'] for r in search_results[:6]]
        labeled_sources, scraped_images = scrape_labeled_sources(urls, max_count=4)
        
        if not labeled_sources and search_results:
            for r in search_results[:4]:
                labeled_sources.append((r.get('url', ''), r.get('content', '')))
        
        scraped_images = [img for img in scraped_images if validate_image_url(img)]

    # 3. Build labeled research material
    labeled_material = ""
    for i, (url, content) in enumerate(labeled_sources):
        truncated = content[:2000] if content else "No content available."
        labeled_material += f"\n[Source {i+1}: {url}]\n{truncated}\n"
    
    if not labeled_material.strip():
        labeled_material = "No research material available. Use general knowledge only."

    system_prompt = MAGAZINE_SYSTEM_PROMPT_V8
    user_prompt = f"""
    Topic (Korean): {topic}
    Original Topic (if any): {original_topic}
    {interest_context}
    {mood_context}
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
    result_json = llm_client.generate_json(system_prompt, user_prompt, temperature=0.7)
    
    # Handle Safety/NSFW Errors
    if "error" in result_json:
        print(f"⚠️ AI Server Policy Triggered: {result_json.get('error')}")
        return result_json

    if result_json.get('thought_process'):
        del result_json['thought_process']
    
    # [Final Language Guard] If the LLM still returns English, force translate the whole object
    result_json = force_translate_magazine_json(result_json)
    result_json = _normalize_magazine_contract(result_json, topic)
    if _needs_contract_repair(result_json):
        print("🛠️ Repairing magazine contract (length/schema)...")
        result_json = _repair_magazine_contract(result_json, topic, labeled_material)
        result_json = force_translate_magazine_json(result_json)
        result_json = _normalize_magazine_contract(result_json, topic)
    
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

    result_json = _expand_short_paragraphs(result_json, topic, labeled_material)
    result_json = _normalize_magazine_contract(result_json, topic)

    # 5. Parallel image searching + moodboard generation.
    # Spring expects create_magazine to return the moodboard when generation succeeds.
    print(f"Parallelizing image searching and moodboard generation...")
    
    used_image_urls = set()
    if result_json.get('cover_image_url') and result_json['cover_image_url'].startswith('http'):
        used_image_urls.add(result_json['cover_image_url'])

    lock = threading.Lock()
    real_tavily_images = [img for img in images]
    indices = {"scraped": 0, "tavily": 0}

    def assign_image_to_target(target, query):
        assigned = False
        if query:
            try:
                pexels_imgs = search_with_pexels(query, orientation='landscape', per_page=3)
                with lock:
                    for img in pexels_imgs:
                        if img not in used_image_urls and validate_image_url(img):
                            target['thumbnail_url' if 'thumbnail_url' in target else 'image_url'] = img
                            used_image_urls.add(img)
                            assigned = True
                            return True
            except Exception as e:
                print(f"Pexels failed: {e}")
        with lock:
            if not assigned:
                while indices["scraped"] < len(scraped_images):
                    img = scraped_images[indices["scraped"]]
                    indices["scraped"] += 1
                    if img not in used_image_urls:
                        target['thumbnail_url' if 'thumbnail_url' in target else 'image_url'] = img
                        used_image_urls.add(img)
                        return True
                while indices["tavily"] < len(real_tavily_images):
                    img = real_tavily_images[indices["tavily"]]
                    indices["tavily"] += 1
                    if img not in used_image_urls and validate_image_url(img):
                        target['thumbnail_url' if 'thumbnail_url' in target else 'image_url'] = img
                        used_image_urls.add(img)
                        return True
        return False

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        from app.core.moodboard_maker import generate_moodboard
        moodboard_future = executor.submit(
            generate_moodboard, topic=topic, user_interests=user_interests,
            magazine_tags=result_json.get('tags', []),
            magazine_titles=[result_json.get('title', 'Untitled')], user_mood=user_mood
        )
        for i, section in enumerate(result_json.get('sections', [])):
            section['display_order'] = i
            if not section.get('thumbnail_url') or not section['thumbnail_url'].startswith('http'):
                q = f"{topic} {section.get('heading', '')} photography"
                futures.append(executor.submit(assign_image_to_target, section, q))
            for para in section.get('paragraphs', []):
                if not para.get('image_url') or not para['image_url'].startswith('http'):
                    pq = para.get('image_search_keyword', f"{topic} {section.get('heading', '')}")
                    futures.append(executor.submit(assign_image_to_target, para, pq))
        for f in futures:
            f.result()
        try:
            # Do not use a timeout here. If this times out inside the
            # ThreadPoolExecutor context, Python still waits for the running
            # future during executor shutdown, but the moodboard result is
            # discarded. Spring expects create_magazine to include moodboard
            # when generation eventually succeeds.
            moodboard_data = moodboard_future.result()
            if moodboard_data and moodboard_data.get('image_url'):
                result_json['moodboard'] = moodboard_data
                print(f"Parallel Moodboard attached: {moodboard_data.get('image_url', '')[:40]}")
            else:
                print(f"Moodboard generation returned no usable image: {moodboard_data}")
        except Exception as e:
            print(f"Moodboard parallel generation failed: {type(e).__name__}: {e}")

    if not result_json.get('cover_image_url') or not result_json['cover_image_url'].startswith('http'):
        with lock:
            if scraped_images: result_json['cover_image_url'] = scraped_images[0]
            elif real_tavily_images: result_json['cover_image_url'] = real_tavily_images[0]
            else: result_json['cover_image_url'] = images[0] if images else ""

    print(f"V8 Magazine created: 2 sections with parallel research and paragraph-level source tracking")
    return result_json
