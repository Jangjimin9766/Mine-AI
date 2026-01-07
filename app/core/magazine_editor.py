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
    Follow the user's instruction while maintaining HIGH QUALITY and INFORMATIVENESS.
    
    CRITICAL RULES:
    1. Prioritize CLEAR, SPECIFIC information
    2. Use refined language but NEVER sacrifice clarity
    3. Include concrete details (names, numbers, facts)
    4. 200-280 characters for content (Korean)
    5. Make it magazine-worthy
    6. ALWAYS preserve the original image_url exactly as provided
    
    Output JSON (use snake_case):
    {
        "heading": "Clear heading in Korean",
        "content": "Informative content in Korean (200-280 chars)",
        "image_url": "EXACT URL from current section (DO NOT change)",
        "layout_hint": "image_left" or "full_width"
    }
    """
    
    user_prompt = f"""
    Current section:
    Heading: {current_section.get('heading', '')}
    Content: {current_section.get('content', '')}
    Image URL: {current_image_url}
    
    User instruction: {instruction}
    
    Rewrite this section following the instruction.
    Keep it in Korean, 200-280 characters for content.
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
    Create HIGH-QUALITY, INFORMATIVE content based on the research provided.
    
    CRITICAL RULES:
    1. Use SPECIFIC information from the research (names, numbers, facts)
    2. Write in a clear, informative, and sophisticated tone
    3. Include concrete details, not vague descriptions
    4. 200-280 characters for content (Korean)
    5. Make it magazine-worthy and engaging
    6. If research is limited, use general knowledge but be specific
    
    Output JSON (use snake_case for field names):
    {
        "heading": "Clear, informative heading in Korean",
        "content": "Detailed, fact-based content in Korean (200-280 chars)",
        "image_url": "Pick the most relevant image URL from the list, or null if none available",
        "layout_hint": "image_left" or "full_width"
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

def edit_section_content(section_data: dict, message: str) -> dict:
    """
    섹션 레벨 상호작용: 의도 분류 기반 섹션 수정
    
    Step 1: 사용자 의도 분류 (APPEND_CONTENT, CHANGE_TONE, FULL_REWRITE 등)
    Step 2: 의도에 따른 적절한 처리 (기존 콘텐츠 보존 기본)
    
    Args:
        section_data: 현재 섹션 데이터
        message: 사용자 수정 요청
    
    Returns:
        Spring이 기대하는 형식의 응답
    """
    from app.core.llm_client import llm_client
    from app.core.prompts import (
        INTENT_CLASSIFICATION_PROMPT,
        APPEND_CONTENT_PROMPT,
        CHANGE_TONE_PROMPT,
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
        # Step 1: 의도 분류
        print(f"✏️ [1/3] Classifying intent for: {message[:50]}...")
        intent_prompt = INTENT_CLASSIFICATION_PROMPT.format(message=message)
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
        
        if intent == 'APPEND_CONTENT':
            # 기존 내용 유지 + 새 내용 추가
            append_prompt = APPEND_CONTENT_PROMPT.format(
                existing_content=original_content,
                message=message
            )
            new_content = llm_client.generate_text(
                "You are a magazine editor. Output HTML content only.",
                append_prompt,
                temperature=0.7
            )
            
        elif intent == 'CHANGE_TONE':
            # 정보 유지 + 톤만 변경
            tone_prompt = CHANGE_TONE_PROMPT.format(
                existing_content=original_content,
                message=message
            )
            new_content = llm_client.generate_text(
                "You are a magazine editor. Output HTML content only.",
                tone_prompt,
                temperature=0.7
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
                
        else:
            # 기본: APPEND_CONTENT와 동일하게 처리
            append_prompt = APPEND_CONTENT_PROMPT.format(
                existing_content=original_content,
                message=message
            )
            new_content = llm_client.generate_text(
                "You are a magazine editor. Output HTML content only.",
                append_prompt,
                temperature=0.7
            )
        
        print(f"✏️ [3/3] Content updated successfully")
        
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

