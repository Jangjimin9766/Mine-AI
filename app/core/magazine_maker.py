from app.core.llm_client import llm_client
import json
from app.core.searcher import search_with_tavily, scrape_with_jina, extract_images_from_content, get_topic_fallback_images, scrape_multiple_with_jina, validate_image_url, search_with_pexels
from app.core.prompts import MAGAZINE_SYSTEM_PROMPT_V4
from concurrent.futures import ThreadPoolExecutor
import threading

def generate_magazine_content(topic: str, user_interests: list = None, user_mood: str = None):
    print(f"🎨 Magazine Editor started for: {topic}")
    
    # 1. 취재 및 LLM 생성 (동기적 진행)
    interest_context = ""
    mood_context = ""
    if user_interests and len(user_interests) > 0:
        interests_str = ', '.join(user_interests)
        interest_context = f"[Reader Profile]\nThis reader is interested in: {interests_str}\n"
    
    if user_mood:
        mood_context = f"[User Mood]\nThe user wants a '{user_mood}' style.\n"

    search_results, images = search_with_tavily(topic, topic=topic)
    
    deep_content = ""
    scraped_images = []
    if search_results:
        urls = [r['url'] for r in search_results[:3]]
        deep_content, scraped_images = scrape_multiple_with_jina(urls, max_count=3)
        
        if not deep_content:
            deep_content = search_results[0].get('content', '')
        
        scraped_images = [img for img in scraped_images if validate_image_url(img)]
        print(f"✅ Validated scraped images: {len(scraped_images)}")

    system_prompt = MAGAZINE_SYSTEM_PROMPT_V4
    user_prompt = f"""
    Topic: {topic}
    {interest_context}
    {mood_context}
    [Research Material]\n{deep_content[:3000]}
    [Available Images]\n{json.dumps(images, ensure_ascii=False)}
    Create a premium magazine article with structured JSON.
    """

    print(f"🧠 AI Crafting V4 magazine...")
    result_json = llm_client.generate_json(system_prompt, user_prompt, temperature=0.7)
    
    if result_json.get('thought_process'):
        del result_json['thought_process']
    
    # 2. [최적화] 병렬 처리 시작 (이미지 검색 + 무드보드 생성)
    print(f"⚡ Parallelizing image searching and moodboard generation...")
    
    used_image_urls = set()
    if result_json.get('cover_image_url') and result_json['cover_image_url'].startswith('http'):
        used_image_urls.add(result_json['cover_image_url'])

    # 스레드 안전을 위한 락(Lock) 및 공유 리소스
    lock = threading.Lock()
    real_tavily_images = [img for img in images]
    
    # 이미지 할당을 위한 인덱스 (락 보호 필요)
    indices = {"scraped": 0, "tavily": 0}

    def assign_image_to_target(target, query):
        """병렬로 실행될 이미지 할당 함수"""
        assigned = False
        
        # 1. Pexels 검색 (가장 고품질)
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
                print(f"⚠️ Pexels failed: {e}")

        # 2. Fallback (Scraped -> Tavily)
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

    # 3. 병렬 작업 큐 구축
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        
        # A. 무드보드 생성 (비동기)
        from app.core.moodboard_maker import generate_moodboard
        moodboard_future = executor.submit(
            generate_moodboard,
            topic=topic,
            user_interests=user_interests,
            magazine_tags=result_json.get('tags', []),
            magazine_titles=[result_json.get('title', 'Untitled')],
            user_mood=user_mood
        )
        
        # B. 섹션 썸네일 검색
        for i, section in enumerate(result_json.get('sections', [])):
            section['display_order'] = i
            if not section.get('thumbnail_url') or not section['thumbnail_url'].startswith('http'):
                q = f"{topic} {section.get('heading', '')} photography"
                futures.append(executor.submit(assign_image_to_target, section, q))
            
            # C. 문단 이미지 검색
            for para in section.get('paragraphs', []):
                if not para.get('image_url') or not para['image_url'].startswith('http'):
                    pq = para.get('image_search_keyword', f"{topic} {section.get('heading', '')}")
                    futures.append(executor.submit(assign_image_to_target, para, pq))

        # 모든 작업 완료 대기
        for f in futures:
            f.result()
            
        # 무드보드 결과 합치기
        try:
            moodboard_data = moodboard_future.result(timeout=60)
            if moodboard_data:
                result_json['moodboard'] = moodboard_data
                print(f"✅ Parallel Moodboard attached")
        except Exception as e:
            print(f"⚠️ Moodboard parallel generation failed: {e}")

    # 4. 커버 이미지 최종 확인 (이미 할당 안 됐으면)
    if not result_json.get('cover_image_url') or not result_json['cover_image_url'].startswith('http'):
        with lock:
            if scraped_images: result_json['cover_image_url'] = scraped_images[0]
            elif real_tavily_images: result_json['cover_image_url'] = real_tavily_images[0]
            else: result_json['cover_image_url'] = images[0] if images else ""

    print(f"✅ Optimized Magazine created: {len(result_json.get('sections', []))} sections")
    return result_json