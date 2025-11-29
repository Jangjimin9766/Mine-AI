import json
from app.core.llm_client import llm_client
from app.core.searcher import search_with_tavily, scrape_with_jina

def generate_magazine_content(topic: str, user_interests: list = None):
    print(f"🎨 Magazine Editor started for: {topic}")
    
    # Build sophisticated interest context
    interest_context = ""
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

    # 1. [취재] Tavily로 정보와 이미지 수집
    search_results, images = search_with_tavily(topic)
    
    # 2. [정독] 상위 1개 글 정독 (Jina)
    deep_content = ""
    if search_results:
        deep_content = scrape_with_jina(search_results[0]['url'])
        if not deep_content:
            deep_content = search_results[0]['content']

    # 3. [편집] LLM에게 매거진 작성 요청
    
    system_prompt = f"""
    You are the Editor-in-Chief of 'M:ine', a premium lifestyle magazine.
    Your mission is to create magazine content that is INFORMATIVE, CLEAR, and SOPHISTICATED.
    
    [CRITICAL INSTRUCTIONS]
    1. You MUST output ONLY a valid JSON object.
    2. **ALL content MUST be written in KOREAN.** (한국어로 작성)
    3. Do not use English unless it is a brand name or proper noun.
    
    [EDITORIAL PHILOSOPHY]
    - Write in a {tone_guidance} tone
    - PRIORITIZE INFORMATION: Deliver concrete, useful information first
    - Use refined language, but NEVER sacrifice clarity for poetry
    - Be specific: Include names, numbers, locations, prices when relevant
    - Think Vogue, GQ, Kinfolk: sophisticated but informative
    - Avoid abstract metaphors - be direct and elegant
    
    [VISUAL STORYTELLING]
    - Choose high-quality, aesthetically striking images
    - Images should be visually sophisticated and magazine-worthy
    - Vary layouts for visual rhythm (alternate image_left and full_width)
    
    [STRUCTURE REQUIREMENTS]
    - Title: Clear and intriguing, not overly poetic (e.g., "제주 겨울, 꼭 가야 할 5곳" not "겨울 바람이 전하는 이야기")
    - Introduction: Set context and preview key information (150-200 chars)
    - Sections: 2-4 sections with CONCRETE information
    - Each section: 200-280 characters of INFORMATIVE content with refined writing
    - Tags: Descriptive and useful (e.g., "제주여행", "겨울추천", "맛집" rather than "감성", "설렘")
    
    [WRITING STYLE]
    - Lead with facts, wrap in sophistication
    - Example BAD: "겨울 바람이 전하는 이야기, 코트 한 벌의 온기..."
    - Example GOOD: "올 겨울 주목할 만한 코트 5가지. 울 100% 소재부터 오버사이즈 핏까지..."
    
    [IMAGE SELECTION]
    - You MUST select actual image URLs from the [Available Images] list provided
    - Pick the most visually striking and relevant images
    - Use different images for cover and sections
    - If no suitable image, use the first available one
    
    Output JSON structure:
    {{
        "title": "Clear, informative title in Korean",
        "introduction": "Context-setting introduction with key information (150-200 chars)",
        "cover_image_url": "SELECT from [Available Images] - most striking image",
        "tags": ["구체적인", "태그들"],
        "sections": [
            {{
                "heading": "Clear, informative subheading",
                "content": "Informative paragraph with specific details (200-280 chars)",
                "image_url": "SELECT from [Available Images] - relevant to this section",
                "layout_hint": "image_left" or "full_width"
            }}
        ]
    }}
    """

    user_prompt = f"""
    Topic: {topic}
    {interest_context}
    
    [Research Material]
    {deep_content[:3000]}
    
    [Available Images]
    {json.dumps(images, ensure_ascii=False)}
    
    Create a magazine article that delivers CLEAR, USEFUL INFORMATION in a sophisticated, refined style.
    Think premium magazine, not poetry book.
    """

    print(f"🧠 AI Crafting informative magazine (tone: {tone_guidance})...")
    
    # llm_client 사용
    result_json = llm_client.generate_json(system_prompt, user_prompt, temperature=0.7)
    
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
    
    # 섹션 이미지 검증
    for i, section in enumerate(result_json.get('sections', [])):
        if not section.get('image_url') or not section['image_url'].startswith('http'):
            section['image_url'] = images[min(i + 1, len(images) - 1)]
            print(f"⚠️ Fixed section {i} image_url to: {section['image_url']}")
    
    print(f"✅ Magazine created with {len(result_json.get('sections', []))} sections")
    
    return result_json