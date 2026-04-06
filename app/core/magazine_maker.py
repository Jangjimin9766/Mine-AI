from app.core.llm_client import llm_client
import json
from app.core.searcher import search_with_tavily, scrape_with_jina, extract_images_from_content, get_topic_fallback_images, scrape_multiple_with_jina, scrape_labeled_sources, validate_image_url, search_with_pexels
from app.core.prompts import MAGAZINE_SYSTEM_PROMPT_V6
from concurrent.futures import ThreadPoolExecutor
import threading

def generate_magazine_content(topic: str, user_interests: list = None, user_mood: str = None):
    print(f"Magazine Editor started for: {topic}")
    
    # 1. Context building
    interest_context = ""
    mood_context = ""
    if user_interests and len(user_interests) > 0:
        interests_str = ', '.join(user_interests)
        interest_context = f"[Reader Profile]\nThis reader is interested in: {interests_str}\n"
    
    if user_mood:
        mood_context = f"[User Mood]\nThe user wants a '{user_mood}' style.\n"

    # Increase max_results to ensure 9+ unique sources
    search_results, images = search_with_tavily(topic, topic=topic)
    
    # 2. [One Source One Paragraph] Labeled source scraping (Up to 9)
    labeled_sources = []
    scraped_images = []
    if search_results:
        # Fetch up to 12 results to pick 9 good ones
        urls = [r['url'] for r in search_results[:12]]
        labeled_sources, scraped_images = scrape_labeled_sources(urls, max_count=9)
        
        # Fallback: if no sources scraped, use Tavily snippets
        if not labeled_sources and search_results:
            for r in search_results[:9]:
                labeled_sources.append((r.get('url', ''), r.get('content', '')))
        
        scraped_images = [img for img in scraped_images if validate_image_url(img)]
        print(f"Validated scraped images: {len(scraped_images)}")

    # 3. Build labeled research material (Source 1 to 9)
    labeled_material = ""
    for i, (url, content) in enumerate(labeled_sources):
        truncated = content[:1500] if content else "No content available."
        labeled_material += f"\n[Source {i+1}: {url}]\n{truncated}\n"
    
    if not labeled_material.strip():
        labeled_material = "No research material available. Use general knowledge only."

    system_prompt = MAGAZINE_SYSTEM_PROMPT_V6
    user_prompt = f"""
    Topic: {topic}
    {interest_context}
    {mood_context}
    [Research Material - LABELED SOURCES]
    {labeled_material}
    [Available Images]
    {json.dumps(images, ensure_ascii=False)}
    Create a premium magazine article with structured JSON.
    Remember the flexible source allocation rule: Prioritize one source per paragraph (9 total), but can share if a source is exceptionally deep.
    Do NOT generate magazine-level subtitle or introduction.
    Every paragraph MUST include a source_url.
    """

    print(f"AI Crafting V6 magazine (V2 Schema Sync)...")
    result_json = llm_client.generate_json(system_prompt, user_prompt, temperature=0.7)
    
    # Handle Safety/NSFW Errors
    if "error" in result_json:
        print(f"⚠️ AI Server Policy Triggered: {result_json.get('error')}")
        return result_json

    if result_json.get('thought_process'):
        del result_json['thought_process']
    
    # 4. Ensure source_url fallback at the paragraph level (V2 Source Fallback Hack)
    source_count = len(labeled_sources)
    for s_idx, section in enumerate(result_json.get('sections', [])):
        for p_idx, para in enumerate(section.get('paragraphs', [])):
            if not para.get('source_url'):
                # Global index for 9 sources: Section 1 (0-2), Section 2 (3-5), Section 3 (6-8)
                fallback_idx = min(s_idx * 3 + p_idx, 8)
                if fallback_idx < source_count:
                    para['source_url'] = labeled_sources[fallback_idx][0]
                elif source_count > 0:
                    para['source_url'] = labeled_sources[0][0]

    # V2 Field Cleanup: Remove unused root fields
    result_json.pop('subtitle', None)
    result_json.pop('introduction', None)
    
    # 5. Parallel image searching + moodboard generation
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
            moodboard_data = moodboard_future.result(timeout=60)
            if moodboard_data:
                result_json['moodboard'] = moodboard_data
                print(f"Parallel Moodboard attached")
        except Exception as e:
            print(f"Moodboard parallel generation failed: {e}")

    if not result_json.get('cover_image_url') or not result_json['cover_image_url'].startswith('http'):
        with lock:
            if scraped_images: result_json['cover_image_url'] = scraped_images[0]
            elif real_tavily_images: result_json['cover_image_url'] = real_tavily_images[0]
            else: result_json['cover_image_url'] = images[0] if images else ""

    print(f"V6 Magazine created: {len(result_json.get('sections', []))} sections with paragraph-level source tracking")
    return result_json
