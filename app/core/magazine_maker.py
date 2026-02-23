from app.core.llm_client import llm_client
import json
from app.core.searcher import search_with_tavily, scrape_with_jina, extract_images_from_content, get_topic_fallback_images
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
    
    # 2. [정독] 상위 1개 글 정독 (Jina)
    deep_content = ""
    scraped_images = []  # 크롤링된 소스에서 추출한 이미지
    if search_results:
        deep_content = scrape_with_jina(search_results[0]['url'])
        if deep_content:
            # [NEW] 크롤링된 소스에서 이미지 URL 추출 (Fix 1)
            scraped_images = extract_images_from_content(deep_content)
            print(f"📰 Scraped images from source: {len(scraped_images)} found")
        else:
            deep_content = search_results[0]['content']

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
    - **CONTENT**: Pure HTML text (<p>, <h3>, <blockquote>). NO `<img>` tags in content.
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
    # [Fix 3] 하드코딩된 Unsplash 그라디언트 대신 주제 기반 fallback 사용
    if not images or len(images) == 0:
        images = get_topic_fallback_images(topic, count=5)
        print(f"⚠️ No Tavily images, using topic-based fallback for '{topic}'")
    
    # Tavily 이미지에서 실제 이미지만 분리 (Unsplash fallback 제외)
    real_tavily_images = [img for img in images if 'unsplash.com/photo-' not in img]
    print(f"📊 Image pool: {len(scraped_images)} scraped, {len(real_tavily_images)} real Tavily, {len(images)} total")
    
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
    from app.core.unsplash_client import search_unsplash_image
    
    # 크롤링 이미지 인덱스 (전역으로 순차 할당)
    scraped_idx = 0
    
    for i, section in enumerate(result_json.get('sections', [])):
        # thumbnail_url 검증 (V4 구조)
        if not section.get('thumbnail_url') or not section['thumbnail_url'].startswith('http'):
            if scraped_idx < len(scraped_images):
                section['thumbnail_url'] = scraped_images[scraped_idx]
                scraped_idx += 1
                print(f"📰 Section {i} thumbnail: scraped image used")
            else:
                section['thumbnail_url'] = images[min(i, len(images) - 1)]
                print(f"⚠️ Section {i} thumbnail: fallback used")
        
        # 레거시 image_url 검증 (V3 호환)
        if not section.get('image_url') or not section['image_url'].startswith('http'):
            section['image_url'] = section.get('thumbnail_url', images[min(i, len(images) - 1)])
        
        # ============================================
        # V4 paragraphs 배열 내 image_url 검증
        # [Fix 2] 우선순위 재정립:
        #   1순위: 크롤링된 소스 이미지 (가장 관련성 높음)
        #   2순위: Tavily 실제 이미지 (Unsplash fallback 제외)
        #   3순위: AI image_search_keyword → Unsplash 검색
        #   4순위: subtitle 기반 Unsplash 검색 (최종 fallback)
        # ============================================
        paragraphs = section.get('paragraphs', [])
        for j, paragraph in enumerate(paragraphs):
            current_url = paragraph.get('image_url', '')
            
            # 이미 유효한 URL이 있으면 스킵
            if current_url and current_url.startswith('http'):
                continue
            
            # ---- 1순위: 크롤링된 소스 이미지 ----
            if scraped_idx < len(scraped_images):
                paragraph['image_url'] = scraped_images[scraped_idx]
                scraped_idx += 1
                print(f"📰 Section {i} paragraph {j}: SCRAPED source image used")
                continue
            
            # ---- 2순위: Tavily 실제 이미지 (Unsplash fallback 제외) ----
            tavily_img_idx = i * 3 + j
            if tavily_img_idx < len(real_tavily_images):
                paragraph['image_url'] = real_tavily_images[tavily_img_idx]
                print(f"📷 Section {i} paragraph {j}: Tavily REAL image used")
                continue
            
            # ---- 3순위: AI image_search_keyword → Unsplash 검색 ----
            search_keyword = paragraph.get('image_search_keyword')
            if search_keyword and len(search_keyword) > 2:
                found_url = search_unsplash_image(search_keyword)
                # Unsplash 성공했고, 그라디언트 fallback이 아닌 경우만 사용
                if found_url and 'unsplash.com/photo-' not in found_url:
                    paragraph['image_url'] = found_url
                    print(f"🎯 Section {i} paragraph {j}: Unsplash keyword matched '{search_keyword}'")
                    continue
                else:
                    print(f"⚠️ Section {i} paragraph {j}: Unsplash keyword '{search_keyword}' → fallback to Tavily cycle")
            
            # ---- 4순위: Tavily 이미지 순환 재사용 (gradient 방지) ----
            # 실제 Tavily 이미지가 있으면 순환(cycle)하여 재사용
            if real_tavily_images:
                cycle_idx = (i * 3 + j) % len(real_tavily_images)
                paragraph['image_url'] = real_tavily_images[cycle_idx]
                print(f"🔄 Section {i} paragraph {j}: Tavily image CYCLED (idx {cycle_idx})")
                continue
            
            # ---- 5순위: subtitle 기반 Unsplash 검색 (최종 fallback) ----
            subtitle = paragraph.get('subtitle', '')
            search_query = f"{topic} {subtitle}" if subtitle else topic
            fallback_url = images[min(i * 3 + j, len(images) - 1)] if images else None
            paragraph['image_url'] = search_unsplash_image(search_query, fallback_url)
            print(f"🖼️ Section {i} paragraph {j}: Unsplash subtitle fallback '{search_query}'")
                
            # [FINAL CHECK] 여전히 image_url이 없으면 주제 기반 fallback
            if not paragraph.get('image_url'):
                topic_fallbacks = get_topic_fallback_images(topic, count=1)
                paragraph['image_url'] = topic_fallbacks[0]
                print(f"🚨 Section {i} paragraph {j}: TOPIC FALLBACK assigned")
        
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