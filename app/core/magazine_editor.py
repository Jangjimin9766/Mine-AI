import json
from app.core.llm_client import llm_client
from app.models.chat import AgentIntent

def analyze_user_intent(user_message: str, magazine_data: dict) -> AgentIntent:
    """
    사용자 메시지를 분석하여 의도 파악
    """
    num_sections = len(magazine_data.get('sections', []))
    
    system_prompt = f"""
    You are an AI editor assistant for M:ine magazine.
    Analyze the user's request and determine what action to take.

    [DOMAIN CONTEXT]
    **Current Magazine Topic**: {magazine_data.get('title', 'N/A')}
    Always interpret the user's message within the context of this Topic. Do NOT confuse terms with unrelated fields (e.g., if topic is Wine, interpret "Potential" as Aging Potential, not games).
    
    Available actions:
    - "regenerate_section": Rewrite a specific section
    - "add_section": Add a new section
    - "delete_section": Remove a section
    - "change_tone": Change the overall tone
    
    CRITICAL RULES:
    1. You MUST always include the "instruction" field with specific details
    2. For Korean ordinal numbers, convert correctly:
       - "첫 번째" or "첫번째" or "1번째" = index 0
       - "두 번째" or "두번째" or "2번째" = index 1
       - "세 번째" or "세번째" or "3번째" = index 2
    3. Current magazine has {num_sections} sections (indices 0 to {num_sections - 1})
    4. If section index is out of range, set target_section_index to null
    
    Respond in JSON:
    {{
        "action": "regenerate_section",
        "target_section_index": 0,
        "instruction": "Make it more emotional and poetic",
        "response_message": "첫 번째 섹션을 더 감성적으로 수정했습니다."
    }}
    
    For "add_section":
    {{
        "action": "add_section",
        "target_section_index": null,
        "instruction": "Add a section about 009's album recommendations",
        "response_message": "009의 앨범 추천 섹션을 추가했습니다."
    }}
    
    For "delete_section":
    {{
        "action": "delete_section",
        "target_section_index": 1,
        "instruction": "Remove the second section",
        "response_message": "두 번째 섹션을 삭제했습니다."
    }}
    """
    
    user_prompt = f"""
    User message: {user_message}
    
    Current magazine structure:
    - Title: {magazine_data.get('title', 'N/A')}
    - Number of sections: {num_sections}
    - Section headings: {[f"{i+1}. {s.get('heading', '')}" for i, s in enumerate(magazine_data.get('sections', []))]}
    
    Analyze the user's intent and provide the action to take.
    REMEMBER: 
    - Always include the "instruction" field
    - Convert Korean ordinals correctly (첫 번째 = 0, 두 번째 = 1)
    - Validate section index is within range [0, {num_sections - 1}]
    """
    
    result = llm_client.generate_json(system_prompt, user_prompt, temperature=0.3)
    
    # Ensure instruction field exists
    if 'instruction' not in result:
        result['instruction'] = user_message
    
    # Validate section index
    if result.get('target_section_index') is not None:
        idx = result['target_section_index']
        if idx < 0 or idx >= num_sections:
            print(f"⚠️ Warning: Section index {idx} out of range [0, {num_sections-1}]")
            result['target_section_index'] = None
    
    return AgentIntent(**result)


def regenerate_section(magazine_data: dict, section_index: int, instruction: str) -> dict:
    """
    특정 섹션만 재생성 - 품질 향상
    """
    sections = magazine_data.get('sections', [])
    
    if section_index < 0 or section_index >= len(sections):
        raise ValueError(f"Invalid section index: {section_index}")
    
    current_section = sections[section_index]
    current_image_url = current_section.get('image_url', '')
    
    system_prompt = """
    You are rewriting a section of a premium lifestyle magazine.
    Follow the user's instruction while maintaining HIGH-DENSITY, INFORMATIVE content.
    
    [EDITORIAL STANDARDS]
    1. **Hyper-Specificity**: Use concrete brand names, numbers, historical facts, and technical data.
    2. **Insightful Narrative**: Don't just list facts. Explain the *significance* and *context*.
    3. **Tone**: Refined, sophisticated, and authoritative formal Korean (습니다/입니다).
    
    [HTML FORMATTING RULES]
    - <h3>: Section-level subheadings (Use at least 1-2 to break long text)
    - <p>: Detailed paragraphs (2-3 sentences each)
    - <strong>: Technical terms or key findings
    - <blockquote>: Powerful quotes or striking statistics
    - <ul><li>: Structured data or lists (only for 3+ items)
    
    [CRITICAL CONSTRAINTS]
    - **Content Length**: 800-1,500 characters (Korean) including HTML tags.
    - **Image URL**: ALWAYS preserve the original image_url exactly as provided.
    - **No Vague Statements**: Avoid generic praise; prove value with evidence.
    
    Output JSON (snake_case):
    {
        "heading": "Clear, brand-like heading",
        "content": "<p>High-quality HTML content...</p>",
        "image_url": "EXACT URL provided",
        "layout_hint": "image_left | full_width"
    }
    """
    
    user_prompt = f"""
    Current section:
    Heading: {current_section.get('heading', '')}
    Content: {current_section.get('content', '')}
    Image URL: {current_image_url}
    
    User instruction: {instruction}
    
    Rewrite this section following the instruction.
    Keep it in Korean, 800-1500 characters for content.
    Make it INFORMATIVE and SPECIFIC, not vague or overly poetic.
    
    IMPORTANT: Use this EXACT image_url in your response: {current_image_url}
    """
    
    from app.core.llm_client import llm_client
    new_section = llm_client.generate_json(system_prompt, user_prompt, temperature=0.7)
    
    # Force preserve original image URL
    new_section['image_url'] = current_image_url
    
    return new_section


def add_new_section(magazine_data: dict, instruction: str) -> dict:
    """
    새 섹션 추가 - 품질 향상을 위해 실제 정보 검색
    """
    from app.core.searcher import search_with_tavily
    
    # 1. 주제 추출 및 검색
    magazine_title = magazine_data.get('title', '')
    search_query = f"{magazine_title} {instruction}"
    
    print(f"🔍 Searching for: {search_query}")
    
    try:
        search_results, images = search_with_tavily(search_query)
    except Exception as e:
        print(f"⚠️ Search failed: {e}, using fallback")
        search_results, images = [], []
    
    # 검색 결과에서 정보 추출
    research_content = ""
    if search_results:
        research_content = "\n".join([
            f"- {result.get('title', '')}: {result.get('content', '')[:200]}"
            for result in search_results[:3]
        ])
    else:
        research_content = "No specific research available. Create content based on general knowledge."
    
    system_prompt = """
    You are adding a new section to a premium lifestyle magazine.
    Create a high-density, authoritative editorial based on the provided research.
    
    [EDITORIAL STANDARDS]
    1. **Data-Driven**: Use specific information from [Research Results] (numbers, names, specs).
    2. **Depth**: Provide context and background. Connect the new section to the magazine's theme.
    3. **Visual Structure**: Use HTML tags to create a structured, readable layout.
    
    [HTML FORMATTING RULES]
    - <h3>: Section-level subheadings (Mandatory for sections over 1000 chars)
    - <p>: Descriptive paragraphs
    - <strong>: Key technical terms or emphasize points
    - <blockquote>: Quotes from research or core insights
    - <ul><li>: Clear lists for facts or features
    
    [CRITICAL RULES]
    - **Length**: 800-1,500 characters (Korean).
    - **Persona**: Editor-in-Chief with deep domain knowledge.
    - **Originality**: Do not repeat existing section topics. Bring a fresh perspective.
    
    Output JSON (snake_case):
    {
        "heading": "Sophisticated heading",
        "content": "<p>Masterpiece HTML content...</p>",
        "image_url": "Pick relevant URL or null",
        "layout_hint": "image_left | full_width"
    }
    """
    
    user_prompt = f"""
    Magazine title: {magazine_title}
    Existing sections: {len(magazine_data.get('sections', []))}
    
    User wants to add: {instruction}
    
    [Research Results]
    {research_content}
    
    [Available Images]
    {images[:5] if images else "No images available"}
    
    Create a new section with SPECIFIC, INFORMATIVE content.
    Keep it in Korean, 800-1500 characters for content.
    Use facts and details from the research.
    Make it as good as the original magazine sections.
    """
    
    from app.core.llm_client import llm_client
    new_section = llm_client.generate_json(system_prompt, user_prompt, temperature=0.7)
    
    # Ensure image_url is not null string
    if not new_section.get('image_url') or new_section.get('image_url') == 'null':
        new_section['image_url'] = None
    
    return new_section


def change_overall_tone(magazine_data: dict, instruction: str) -> list:
    """
    전체 톤 변경 (모든 섹션 재생성)
    """
    sections = magazine_data.get('sections', [])
    new_sections = []
    
    for i, section in enumerate(sections):
        new_section = regenerate_section(
            magazine_data=magazine_data,
            section_index=i,
            instruction=f"{instruction} (Section {i+1}: {section.get('heading', '')})"
        )
        new_sections.append(new_section)
    
    return new_sections


# ==========================================
# 섹션 레벨 편집 (Section-Level Editing)
# ==========================================

def strip_markdown_codeblocks(content: str) -> str:
    """
    LLM 출력에서 마크다운 코드블럭을 제거합니다.
    예: ```html\n<p>내용</p>\n``` → <p>내용</p>
    """
    import re
    
    # ```html ... ``` 또는 ``` ... ``` 패턴 제거
    pattern = r'```(?:html|HTML)?\s*([\s\S]*?)\s*```'
    match = re.search(pattern, content)
    if match:
        return match.group(1).strip()
    
    # 코드블럭이 없으면 그대로 반환
    return content.strip()


def edit_section_content(section_data: dict, message: str, topic: str = "Magazine Content") -> dict:
    """
    섹션 레벨 상호작용: 의도 분류 기반 섹션 수정
    
    Step 1: 사용자 의도 분류 (APPEND_CONTENT, CHANGE_TONE, FULL_REWRITE 등)
    Step 2: 의도에 따른 적절한 처리 (기존 콘텐츠 보존 기본)
    
    Args:
        section_data: 현재 섹션 데이터
        message: 사용자 수정 요청
        topic: 잡지의 전체 주제 (할루시네이션 방지용)
    
    Returns:
        Spring이 기대하는 형식의 응답
    """
    from app.core.llm_client import llm_client
    from app.core.prompts import (
        INTENT_CLASSIFICATION_PROMPT_V2,  # V1 → V2로 업그레이드!
        APPEND_CONTENT_PROMPT_V2,         # V1 → V2로 업그레이드!
        CHANGE_TONE_PROMPT_V2,            # V1 → V2로 업그레이드!
        FULL_REWRITE_PROMPT,
        SECTION_EDIT_PROMPT
    )
    
    # 원본 데이터 보존
    original_heading = section_data.get('heading', '')
    original_content = section_data.get('content', '')
    original_image_url = section_data.get('image_url', '')
    original_layout_hint = section_data.get('layout_hint', 'image_left')
    original_layout_type = section_data.get('layout_type', 'basic')
    original_caption = section_data.get('caption', '')
    
    try:
        # Step 1: 의도 분류 (V2 프롬프트 사용 - 더 세밀한 분류)
        print(f"✏️ [1/3] Classifying intent (V2) for topic '{topic}': {message[:50]}...")
        intent_prompt = INTENT_CLASSIFICATION_PROMPT_V2.format(
            topic=topic,
            existing_content=original_content,
            message=message
        )
        intent_result = llm_client.generate_json(
            "You are an intent classifier. Output valid JSON only.",
            intent_prompt,
            temperature=0.3
        )
        
        intent = intent_result.get('intent', 'APPEND_CONTENT')
        print(f"✏️ [2/3] Detected intent: {intent}")
        
        # Step 2: 의도별 처리
        new_content = original_content
        new_heading = original_heading
        
        if intent in ['ADD_INFORMATION', 'ADD_EXAMPLES', 'APPEND_CONTENT']:
            # 이미지 검색 (Tavily 사용)
            from app.core.searcher import search_with_tavily
            import json
            
            print(f"🔍 Searching images for: {message[:30]}...")
            try:
                _, images = search_with_tavily(message)
                available_images = json.dumps(images[:5], ensure_ascii=False) if images else "[]"
            except Exception as e:
                print(f"⚠️ Image search failed: {e}")
                available_images = "[]"
            
            # 기존 내용 유지 + 새 내용 추가 (V2 프롬프트 - 더 명확한 제약)
            append_prompt = APPEND_CONTENT_PROMPT_V2.format(
                topic=topic,
                existing_content=original_content,
                message=message,
                available_images=available_images
            )
            new_content = llm_client.generate_text(
                "You are a magazine editor. Output HTML content only. Include images using <img> tags.",
                append_prompt,
                temperature=0.6
            )
            
        elif intent in ['CHANGE_TONE_CASUAL', 'CHANGE_TONE_FORMAL', 'CHANGE_TONE_EMOTIONAL', 'CHANGE_TONE']:
            # 정보 유지 + 톤만 변경 (V2 프롬프트 - 정보 손실 방지 강화)
            tone_prompt = CHANGE_TONE_PROMPT_V2.format(
                topic=topic,
                existing_content=original_content,
                message=message
            )
            new_content = llm_client.generate_text(
                "You are a magazine editor. Output HTML content only.",
                tone_prompt,
                temperature=0.6
            )
            
        elif intent == 'FULL_REWRITE':
            # 전체 재작성 (명시적 요청 시에만)
            rewrite_prompt = FULL_REWRITE_PROMPT.format(
                heading=original_heading,
                message=message
            )
            new_content = llm_client.generate_text(
                "You are a magazine editor. Output HTML content only.",
                rewrite_prompt,
                temperature=0.7
            )
            
        elif intent == 'CHANGE_HEADING':
            # 제목만 변경
            heading_result = llm_client.generate_json(
                "Generate a new heading based on the request. Output JSON: {\"heading\": \"새 제목\"}",
                f"현재 제목: {original_heading}\n요청: {message}",
                temperature=0.7
            )
            new_heading = heading_result.get('heading', original_heading)
            
        elif intent == 'DELETE_PARAGRAPH':
            # 문단 삭제 (BeautifulSoup 사용)
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(original_content, 'html.parser')
                paragraphs = soup.find_all(['p', 'h3', 'ul', 'ol'])
                target_idx = intent_result.get('target_paragraph', -1)
                if target_idx is not None and 0 <= target_idx < len(paragraphs):
                    paragraphs[target_idx].decompose()
                new_content = str(soup)
            except ImportError:
                # BeautifulSoup 없으면 fallback
                new_content = original_content
                
        elif intent == 'SIMPLIFY':
            # 간단하게 (V2의 CHANGE_TONE 프롬프트 재사용)
            tone_prompt = CHANGE_TONE_PROMPT_V2.format(
                existing_content=original_content,
                message="간단하게, 짧게, 쉽게"
            )
            new_content = llm_client.generate_text(
                "You are a magazine editor. Output HTML content only.",
                tone_prompt,
                temperature=0.6
            )
            
        elif intent == 'EXPAND':
            # 자세하게 (V2의 CHANGE_TONE 프롬프트 재사용)
            tone_prompt = CHANGE_TONE_PROMPT_V2.format(
                existing_content=original_content,
                message="더 자세하게, 길게, 깊이있게"
            )
            new_content = llm_client.generate_text(
                "You are a magazine editor. Output HTML content only.",
                tone_prompt,
                temperature=0.7
            )
                
        else:
            # 기본: APPEND_CONTENT와 동일하게 처리
            from app.core.searcher import search_with_tavily
            import json
            
            print(f"🔍 Searching images for: {message[:30]}...")
            try:
                _, images = search_with_tavily(message)
                available_images = json.dumps(images[:5], ensure_ascii=False) if images else "[]"
            except Exception as e:
                print(f"⚠️ Image search failed: {e}")
                available_images = "[]"
            
            append_prompt = APPEND_CONTENT_PROMPT_V2.format(
                existing_content=original_content,
                message=message,
                available_images=available_images
            )
            new_content = llm_client.generate_text(
                "You are a magazine editor. Output HTML content only. Include images using <img> tags.",
                append_prompt,
                temperature=0.6
            )
        
        print(f"✏️ [3/3] Content updated successfully")
        
        # 마크다운 코드블럭 제거 (LLM이 ```html ... ``` 형태로 출력하는 경우)
        new_content = strip_markdown_codeblocks(new_content)
        
        # 결과 반환 (Spring 형식)
        return {
            "intent": intent.lower(),
            "success": True,
            "updated_section": {
                "id": section_data.get('id'),
                "heading": new_heading,
                "content": new_content,
                "image_url": original_image_url,  # 항상 보존
                "layout_hint": original_layout_hint,
                "layout_type": original_layout_type,
                "caption": original_caption
            }
        }
        
    except Exception as e:
        print(f"❌ edit_section_content error: {e}")
        import traceback
        print(traceback.format_exc())
        return {
            "intent": "modify_content",
            "success": False,
            "error": str(e),
            "updated_section": None
        }


def delete_section(magazine_data: dict, section_index: int) -> dict:
    """
    매거진 레벨: 섹션 삭제
    
    Returns:
        {
            "intent": "delete_section",
            "success": True,
            "section_index": 2
        }
    """
    sections = magazine_data.get('sections', [])
    
    if section_index < 0 or section_index >= len(sections):
        return {
            "intent": "delete_section",
            "success": False,
            "error": f"Invalid section index: {section_index}"
        }
    
    return {
        "intent": "delete_section",
        "success": True,
        "section_index": section_index
    }