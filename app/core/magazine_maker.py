from app.core.llm_client import llm_client
import json
from app.core.searcher import search_with_tavily, scrape_with_jina, extract_images_from_content, get_topic_fallback_images, scrape_multiple_with_jina, validate_image_url
from app.core.prompts import MAGAZINE_SYSTEM_PROMPT_V4  # V3 → V4로 변경

def generate_magazine_content(topic: str, user_interests: list = None, user_mood: str = None):
    print(f"🎨 Magazine Editor started for: {topic}")
    
    # Build sophisticated interest context
    interest_context = ""
    mood_context = ""
    tone_guidance = "clear, informative, and sophisticated"
    
    if user_interests and len(user_interests) > 0:
        interests_str = ', '.join(user_interests)
        interest_context = f"""
[Reader Profile]
This reader is interested in: {interests_str}

Connect the topic to their interests when relevant, but keep it natural and informative.
"""
        
        # Adjust tone based on interests (but keep it informative)
        if any(interest.lower() in ['art', 'music', 'beauty'] for interest in user_interests):
            tone_guidance = "refined, aesthetic-focused, and informative"
        elif any(interest.lower() in ['sports', 'health', 'cycling'] for interest in user_interests):
            tone_guidance = "energetic, practical, and informative"
        elif any(interest.lower() in ['travel', 'food', 'lifestyle'] for interest in user_interests):
            tone_guidance = "experiential, detailed, and informative"

    # Build user mood context
    if user_mood:
        mood_context = f"""
[User Mood]
The user wants a '{user_mood}' style. Adjust your tone accordingly:
- If 'Classic': Write elegantly and timelessly.
- If 'Fun': Write wittily and energetically.
- If 'Minimal': Write concisely with clean aesthetics.
- If 'Bold': Write with strong statements and impact.
"""
        print(f"🎭 User mood: {user_mood}")

    # 1. [취재] Tavily로 정보와 이미지 수집
    search_results, images = search_with_tavily(topic, topic=topic)
    
    # 2. [정독] 상위 3개 글 정독 (Jina) — 이미지 풀 최대 확보
    deep_content = ""
    scraped_images = []  # 크롤링된 소스에서 추출한 이미지
    if search_results:
        urls = [r['url'] for r in search_results[:3]]
        deep_content, scraped_images = scrape_multiple_with_jina(urls, max_count=3)
        
        # 크롤링 실패 시 검색 결과 본문을 fallback으로 사용
        if not deep_content:
            deep_content = search_results[0].get('content', '')
        
        # 크롤링 이미지 유효성 사전 검증 (엑박 방지)
        validated_scraped = []
        for img in scraped_images:
            if validate_image_url(img):
                validated_scraped.append(img)
            else:
                print(f"🗑️ Removed invalid scraped image: {img[:60]}...")
        scraped_images = validated_scraped
        print(f"✅ Validated scraped images: {len(scraped_images)} passed")

    # 3. [편집] LLM에게 매거진 작성 요청 (V4 프롬프트 - 더 구체적이고 품질 높게)
    system_prompt = MAGAZINE_SYSTEM_PROMPT_V4  # V3에서 V4로 업그레이드!

    user_prompt = f"""
    Topic: {topic}
    {interest_context}
    {mood_context}
    
    [Research Material]
    {deep_content[:3000]}
    
    [Available Images]
    {json.dumps(images, ensure_ascii=False)}
    
    Create a premium magazine article with these requirements:
    - **LAYOUT**: Zigzag flow. Alternate between `split_left` and `split_right`.
    - **CONTENT**: Markdown text in each paragraph (`text` field). Use `>`, lists (`-`, `1.`), and `**bold**` naturally. NO HTML tags.
    - **IMAGES**: Assign a relevant image_url to each section.
    - **TONE**: Sophisticated Korean (습니다/입니다 formal tone).
    - **STRUCTURE**: 4-6 Sections total.
    """

    print(f"🧠 AI Crafting V4 magazine with enhanced quality standards...")
    
    # llm_client 사용 (안정성과 창의성의 균형을 위해 0.7로 설정)
    result_json = llm_client.generate_json(system_prompt, user_prompt, temperature=0.7)
    
    # [CoT 확인] 에디터의 생각 읽기
    if result_json.get('thought_process'):
        print(f"🤔 Editor's Thought: {result_json['thought_process'][:100]}...")
        # 클라이언트에게는 굳이 생각을 보낼 필요가 없다면 삭제 (Spring DTO 호환성)
        del result_json['thought_process']
    
    # 🔒 이미지 URL 검증 및 보정
    if not images or len(images) == 0:
        # Tavily 이미지가 없으면 추가 검색 시도
        print(f"⚠️ No Tavily images, attempting additional search for '{topic}'")
        extra_results, extra_images = search_with_tavily(f"{topic} 사진 이미지", topic=topic)
        images = extra_images
    
    # Tavily에서 가져온 실제 이미지
    real_tavily_images = [img for img in images]
    print(f"📊 Image pool: {len(scraped_images)} scraped, {len(real_tavily_images)} Tavily, {len(images)} total")
    
    # 커버 이미지 검증: 크롤링 이미지 우선 → Tavily → 주제 fallback
    if not result_json.get('cover_image_url') or not result_json['cover_image_url'].startswith('http'):
        if scraped_images:
            result_json['cover_image_url'] = scraped_images[0]
            print(f"✅ Cover image from scraped source: {scraped_images[0][:60]}...")
        elif real_tavily_images:
            result_json['cover_image_url'] = real_tavily_images[0]
            print(f"✅ Cover image from Tavily: {real_tavily_images[0][:60]}...")
        else:
            result_json['cover_image_url'] = images[0]
            print(f"⚠️ Cover image fallback: {images[0][:60]}...")
    
    # 섹션 이미지 검증 및 display_order 추가
    # 전역 사용 URL 저장 (중복 방지)
    used_image_urls = set()
    if result_json.get('cover_image_url'):
        used_image_urls.add(result_json['cover_image_url'])

    # 크롤링 이미지 인덱스 (전역으로 순차 할당)
    scraped_idx = 0
    tavily_img_idx = 0
    
    for i, section in enumerate(result_json.get('sections', [])):
        # thumbnail_url 검증 (V4 구조)
        if not section.get('thumbnail_url') or not section['thumbnail_url'].startswith('http') or not validate_image_url(section['thumbnail_url']):
            assigned = False
            # 1. 크롤링 이미지 우선 시도
            while scraped_idx < len(scraped_images):
                img = scraped_images[scraped_idx]
                scraped_idx += 1
                if img not in used_image_urls and validate_image_url(img):
                    section['thumbnail_url'] = img
                    used_image_urls.add(img)
                    assigned = True
                    print(f"📰 Section {i} thumbnail: scraped image used")
                    break
            
            # 2. 크롤링 본문 이미지가 없으면 초기 검색 이미지 풀에서 할당
            if not assigned:
                for img in images:
                    if img not in used_image_urls and validate_image_url(img):
                        section['thumbnail_url'] = img
                        used_image_urls.add(img)
                        assigned = True
                        break
            
            # 3. [NEW] 그래도 없으면 해당 섹션 주제로 무조건 강제 검색하여 진짜 이미지를 가져옴 (유저 필수 요청)
            if not assigned:
                print(f"⚠️ Section {i} thumbnail: Pool exhausted. Forcing a fresh Tavily search for a real image.")
                heading = section.get('heading', topic)
                fallback_query = f"{topic} {heading} 사진"
                try:
                    _, extra_imgs = search_with_tavily(fallback_query, topic=topic)
                    for img in extra_imgs:
                        if validate_image_url(img) and img not in used_image_urls: # 중복 방지 조건 추가
                            section['thumbnail_url'] = img
                            used_image_urls.add(img)
                            assigned = True
                            print(f"✅ Section {i} thumbnail: Successfully fetched a real fallback image via Tavily")
                            break
                except Exception as e:
                    print(f"❌ Force fallback search failed: {e}")

            # 4. 정 안되면 중복 없는 새로운 이미지 확보를 위해 더 넓은 키워드로 마지막 검색 시도
            if not assigned:
                print(f"⚠️ Section {i} thumbnail: Still no unique image. Trying broad search.")
                broad_query = f"{topic} 고화질 배경화면"
                try:
                    _, extra_imgs = search_with_tavily(broad_query, topic=topic)
                    for img in extra_imgs:
                        if validate_image_url(img) and img not in used_image_urls:
                             section['thumbnail_url'] = img
                             used_image_urls.add(img)
                             assigned = True
                             print(f"✅ Section {i} thumbnail: broad fallback success")
                             break
                except Exception as e:
                    pass
                
            if not assigned and images:
                 # 정말로 새로운 이미지를 찾지 못한 최악의 경우, 중복 허용을 방지하기 위해 
                 # 플레이스홀더를 쓰거나 차라리 빈 값으로 둡니다. 하지만 여기선 일단 첫번째 유효 이미지를 쓰되,
                 # 중복 방지를 원하셨으므로 차라리 검색 결과 중 가장 안 쓴 이미지를 찾으려는 노력은 생략하고
                 # 중복이 발생하더라도 앱이 터지지 않도록 최후의 안전망만 유지 (단, 이 단계까지 올 확률은 극히 낮음)
                 unassigned_imgs = [img for img in images if img not in used_image_urls]
                 if unassigned_imgs:
                     section['thumbnail_url'] = unassigned_imgs[0]
                     used_image_urls.add(unassigned_imgs[0])
                 else:
                     section['thumbnail_url'] = images[0]
                 print(f"⚠️ Section {i} thumbnail: ultimate fallback (might be duplicate)")
        
        # 레거시 image_url 검증 (V3 호환)
        if not section.get('image_url') or not section['image_url'].startswith('http'):
            section['image_url'] = section.get('thumbnail_url', images[0] if images else None)
        
        # ============================================
        # V4 paragraphs 배열 내 image_url 검증
        # 우선순위 (Jina 크롤링 + Tavily 전용):
        #   1순위: 크롤링된 소스 이미지 (Jina 3개 URL, 가장 관련성 높음)
        #   2순위: Tavily 실제 이미지 (검색 결과에 포함된 이미지)
        #   3순위: Tavily 추가 검색 (주제 변형 검색어로 이미지 확보)
        # ============================================
        paragraphs = section.get('paragraphs', [])
        for j, paragraph in enumerate(paragraphs):
            current_url = paragraph.get('image_url', '')
            
            # 이미 유효한 URL이 있으면 검증 후 스킵
            if current_url and current_url.startswith('http'):
                if validate_image_url(current_url):
                    continue
                else:
                    print(f"⚠️ Section {i} paragraph {j}: AI-assigned URL invalid, re-assigning")
                    paragraph['image_url'] = None
            
            assigned = False
            
            # ---- 1순위: 크롤링된 소스 이미지 (Jina 3개 URL에서 수집, 사전 검증 완료) ----
            while scraped_idx < len(scraped_images):
                img = scraped_images[scraped_idx]
                scraped_idx += 1
                if img not in used_image_urls:
                    paragraph['image_url'] = img
                    used_image_urls.add(img)
                    assigned = True
                    print(f"📰 Section {i} paragraph {j}: SCRAPED source image used")
                    break
            
            if assigned: continue
            
            # ---- 2순위: Tavily 실제 이미지 (검증 포함) ----
            while tavily_img_idx < len(real_tavily_images):
                img = real_tavily_images[tavily_img_idx]
                tavily_img_idx += 1
                if img not in used_image_urls and validate_image_url(img):
                    paragraph['image_url'] = img
                    used_image_urls.add(img)
                    assigned = True
                    print(f"📷 Section {i} paragraph {j}: Tavily REAL image used (validated)")
                    break
                    
            if assigned: continue
            
            # ---- 3순위: Tavily 추가 검색으로 이미지 확보 ----
            if not assigned:
                search_keyword = paragraph.get('image_search_keyword', '')
                subtitle = paragraph.get('subtitle', '')
                extra_query = f"{topic} {subtitle}" if subtitle else f"{topic} {search_keyword}"
                
                try:
                    _, extra_imgs = search_with_tavily(extra_query, topic=topic)
                    for img in extra_imgs:
                        if img not in used_image_urls and validate_image_url(img):
                            paragraph['image_url'] = img
                            used_image_urls.add(img)
                            assigned = True
                            print(f"🔄 Section {i} paragraph {j}: Tavily EXTRA search image used")
                            break
                except Exception as e:
                    print(f"⚠️ Extra Tavily search failed: {e}")
            
            if assigned: continue
            
            # ---- 최종: 이미 사용된 이미지라도 중복 허용 (빈 이미지보다 중복이 나음) 코드를 수정하여 중복 방지 강화 ----
            if not paragraph.get('image_url'):
                print(f"⚠️ Section {i} paragraph {j}: Still no unique image. Forcing broad search.")
                broad_query = f"{topic} 고화질 풍경"
                try:
                    _, extra_imgs = search_with_tavily(broad_query, topic=topic)
                    for img in extra_imgs:
                        if img not in used_image_urls and validate_image_url(img):
                            paragraph['image_url'] = img
                            used_image_urls.add(img)
                            assigned = True
                            print(f"✅ Section {i} paragraph {j}: broad fallback success")
                            break
                except Exception as e:
                    pass
                
                if not paragraph.get('image_url'):
                    # 정말로 모든 방법이 다 실패했을 때만 최악의 대안 (미사용 이미지 우선 탐색)
                    all_available = scraped_images + real_tavily_images
                    unused = [img for img in all_available if img not in used_image_urls]
                    if unused:
                        paragraph['image_url'] = unused[0]
                        used_image_urls.add(unused[0])
                        print(f"⚠️ Section {i} paragraph {j}: Used remaining unused image")
                    elif all_available:
                        paragraph['image_url'] = all_available[0]
                        print(f"❌ Section {i} paragraph {j}: DUPLICATE image assigned (out of unique images)")
                    else:
                        print(f"❌ Section {i} paragraph {j}: NO images available at all")
        
        # display_order 자동 부여 (그리드 순서)
        section['display_order'] = i
        # layout_hint 기본값 설정
        if not section.get('layout_hint'):
            section['layout_hint'] = 'image_left'

    # 4. [부록] 매거진과 1:1 매칭되는 무드보드 생성 (Local SDXL)
    from app.core.moodboard_maker import generate_moodboard
    
    print(f"🎨 Generating matching moodboard for magazine: {result_json.get('title')}")
    
    moodboard_data = generate_moodboard(
        topic=topic,
        user_interests=user_interests,
        magazine_tags=result_json.get('tags', []),
        magazine_titles=[result_json.get('title', 'Untitled')]
    )
    
    if moodboard_data:
        result_json['moodboard'] = moodboard_data
        print(f"✅ Moodboard attached to magazine")
    
    print(f"✅ Magazine with moodboard created: {len(result_json.get('sections', []))} sections")
    
    return result_json