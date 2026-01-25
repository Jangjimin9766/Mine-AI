from app.core.llm_client import llm_client
import json
from app.core.searcher import search_with_tavily, scrape_with_jina
from app.core.prompts import MAGAZINE_SYSTEM_PROMPT_V5  # V4 → V5로 변경

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
    if search_results:
        deep_content = scrape_with_jina(search_results[0]['url'])
        if not deep_content:
            deep_content = search_results[0]['content']

    # 3. [편집] LLM에게 매거진 작성 요청 (V5 프롬프트 - 하이엔드 큐레이션 및 정보 밀도 강화)
    system_prompt = MAGAZINE_SYSTEM_PROMPT_V5  # V4에서 V5로 업그레이드!

    user_prompt = f"""
    Topic: {topic}
    {interest_context}
    {mood_context}
    
    [Research Material]
    {deep_content[:3000]}
    
    [Available Images]
    {json.dumps(images, ensure_ascii=False)}
    
    Create a premium magazine article with these requirements:
    - At least 4-6 sections with clear hierarchy
    - Each section must have 3+ concrete facts/examples
    - Use specific numbers, names, locations (not vague statements)
    - First section should be layout_type "hero"
    - Mix of split_left, split_right, and basic layouts
    - Sophisticated Korean (습니다/입니다 formal tone)
    
    Remember: Readers should learn something valuable, not just be entertained.
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
        # 이미지가 없으면 플레이스홀더 사용
        images = [
            "https://images.unsplash.com/photo-1557683316-973673baf926?w=1200",
            "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=1200",
            "https://images.unsplash.com/photo-1557682250-33bd709cbe85?w=1200",
        ]
    
    # 커버 이미지 검증
    if not result_json.get('cover_image_url') or not result_json['cover_image_url'].startswith('http'):
        result_json['cover_image_url'] = images[0]
        print(f"⚠️ Fixed cover_image_url to: {images[0]}")
    
    # 섹션 이미지 검증 및 display_order 추가
    for i, section in enumerate(result_json.get('sections', [])):
        if not section.get('image_url') or not section['image_url'].startswith('http'):
            section['image_url'] = images[min(i + 1, len(images) - 1)]
            print(f"⚠️ Fixed section {i} image_url to: {section['image_url']}")
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