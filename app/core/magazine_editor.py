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
