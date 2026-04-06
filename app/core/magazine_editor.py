# FORCE_REDEPLOY_FOR_STRUCTURE_SYNC_V2
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
    특정 섹션만 재생성 - Spring Boot가 기대하는 paragraphs 배열 구조(3개 문단)로 반환
    """
    from app.core.llm_client import llm_client
    from app.core.searcher import search_with_pexels, search_with_tavily
    
    sections = magazine_data.get('sections', [])
    if section_index < 0 or section_index >= len(sections):
        raise ValueError(f"Invalid section index: {section_index}")
    
    current_section = sections[section_index]
    magazine_title = magazine_data.get('title', '')
    
    # [Language Guard] Pre-translate instruction if English
    original_instruction = instruction
    if is_mostly_english(instruction):
        instruction = translate_to_korean(instruction, "edit instruction")
        print(f"  -> Instruction translated: {original_instruction} -> {instruction}")

    # [One Source One Use]
    source_url = current_section.get('source_url')
    research_content = ""
    
    if not source_url:
        search_query = f"{magazine_title} {current_section.get('heading', '')} {instruction}"
        try:
            results, _ = search_with_tavily(search_query)
            if results:
                source_url = results[0].get('url')
                research_content = results[0].get('content', '')[:1000]
        except: pass
    
    system_prompt = """
    You are a professional Korean magazine editor rewriting a section for 'M:ine'.
    
    [EDITORIAL MISSION]
    - Persona: Refined, authoritative Korean editor.
    - Language: ALL content MUST be in Korean.
    - Structure: EXACTLY 3 paragraphs in the "paragraphs" array.
    - Each paragraph: subtitle (10-30 chars) + text (600-800 characters REQUIRED) + image_search_keyword (English, 3 words)
    - Heading: Korean, concise.
    
    [SOURCE INTEGRITY]
    - Every paragraph MUST include a `source_url`.
    - Content: {instruction}

    Output JSON EXACTLY:
    {
        "heading": "섹션 제목",
        "paragraphs": [
            {
                "subtitle": "소제목 1",
                "text": "본문 1",
                "image_search_keyword": "kw1",
                "source_url": "https://..."
            },
            {
                "subtitle": "소제목 2",
                "text": "본문 2",
                "image_search_keyword": "kw2",
                "source_url": "https://..."
            },
            {
                "subtitle": "소제목 3",
                "text": "본문 3",
                "image_search_keyword": "kw3",
                "source_url": "https://..."
            }
        ]
    }
    """.replace("{instruction}", instruction)
    
    user_prompt = f"""
    Magazine: {magazine_title}
    Current Section Heading: {current_section.get('heading')}
    Current Section Text: {current_section.get('paragraphs', [{}])[0].get('text', '')[:200]}...
    Instruction: {instruction}
    Research: {research_content}
    """
    
    new_data = llm_client.generate_json(system_prompt, user_prompt, temperature=0.7)
    
    if "error" in new_data:
        return new_data

    # 이미지 검색 (기존 이미지 활용 또는 신규 검색)
    current_paras = current_section.get('paragraphs', [])
    for i, para in enumerate(new_data.get('paragraphs', [])):
        keyword = para.get('image_search_keyword')
        para['image_url'] = None
        
        # [Sync] source_url fallback if missing
        if not para.get('source_url'):
            para['source_url'] = source_url

        # 기존 이미지가 있다면 최대한 유지
        if i < len(current_paras):
            para['image_url'] = current_paras[i].get('imageUrl') or current_paras[i].get('image_url')
        
        if not para['image_url'] and keyword:
            try:
                imgs = search_with_pexels(keyword, orientation='landscape', per_page=1)
                if imgs: para['image_url'] = imgs[0]
            except: pass

    # 썸네일 처리
    new_data['thumbnail_url'] = current_section.get('thumbnail_url') or current_section.get('image_url')
    if not new_data['thumbnail_url']:
        try:
            imgs = search_with_pexels(new_data.get('heading', 'lifestyle'), orientation='landscape', per_page=1)
            if imgs: new_data['thumbnail_url'] = imgs[0]
        except: pass
    
    # V2 Cleanup: Ensure no root-level intro/subtitle
    new_data.pop('subtitle', None)
    new_data.pop('introduction', None)
    
    # [Final Language Guard] Force translate if AI still returns English
    new_data = force_translate_section(new_data)
    
    return new_data


def add_new_section(magazine_data: dict, instruction: str) -> dict:
    """
    새 섹션 추가 - Spring Boot가 기대하는 paragraphs 배열 구조(3개 문단)로 반환
    """
    from app.core.searcher import search_with_tavily, search_with_pexels, scrape_labeled_sources
    from app.core.llm_client import llm_client
    from app.core.utils import is_mostly_english, translate_to_korean, force_translate_section
    import json
    
    # 1. 주제 추출 및 [Source 1, 2, 3] 확보
    magazine_title = magazine_data.get('title', '')
    
    # [Language Guard] Pre-translate instruction if English
    if is_mostly_english(instruction):
        instruction = translate_to_korean(instruction, "new section instruction")

    search_query = f"{magazine_title} {instruction}"
    
    print(f"🔍 Searching sources for new section: {search_query}")
    
    labeled_sources = []
    images = []
    try:
        search_results, images = search_with_tavily(search_query, topic=magazine_title)
        if search_results:
            from app.core.searcher import scrape_labeled_sources
            urls = [r['url'] for r in search_results[:5]]
            labeled_sources, _ = scrape_labeled_sources(urls, max_count=3)
    except Exception as e:
        print(f"⚠️ Search failed: {e}")
    
    research_content = ""
    for i, (url, content) in enumerate(labeled_sources):
        research_content += f"\n[Source {i+1}: {url}]\n{content[:1000]}\n"
    
    if not research_content:
        research_content = "No specific research available. Use general knowledge."
    
    # 기존 섹션 헤딩 (중복 방지)
    existing_headings = [s.get('heading', '') for s in magazine_data.get('sections', [])]
    
    system_prompt = """
    You are a professional Korean magazine editor adding a new section to 'M:ine'.
    
    [EDITORIAL MISSION]
    - Persona: Professional, data-driven, sophisticated.
    - Language: ALL content MUST be in Korean.
    - Structure: EXACTLY 3 sections, 3 paragraphs each.
    - Every paragraph MUST include a `source_url`.
    - No Root Metadata: Do NOT include root-level `introduction` or `subtitle`.

    [CONTENT RULES]
    - Heading: Korean, brand-like.
    - Paragraph: subtitle (Korean) + text (600-800 chars Korean) + image_search_keyword (English nouns).
    - Originality: Do not repeat existing topics: {existing_headings}

    Output JSON EXACTLY:
    {
        "heading": "섹션 제목",
        "thumbnail_search_keyword": "english landscape keyword",
        "paragraphs": [
            {
                "subtitle": "소제목 1",
                "text": "본문 내용 1",
                "image_search_keyword": "keyword1",
                "source_url": "Source 1 URL"
            },
            {
                "subtitle": "소제목 2",
                "text": "본문 내용 2",
                "image_search_keyword": "keyword2",
                "source_url": "Source 2 URL"
            },
            {
                "subtitle": "소제목 3",
                "text": "본문 내용 3",
                "image_search_keyword": "keyword3",
                "source_url": "Source 3 URL"
            }
        ]
    }
    """
    
    user_prompt = f"""
    Magazine title: {magazine_title}
    User wants to add: {instruction}
    Existing headings: {existing_headings}
    [Research Results]
    {research_content}
    """
    
    new_section = llm_client.generate_json(system_prompt, user_prompt, temperature=0.7)
    
    if "error" in new_section:
        return new_section

    # 2. 이미지 검색 및 source_url 보정 (V2 Fallback Hack)
    source_count = len(labeled_sources)
    for i, para in enumerate(new_section.get('paragraphs', [])):
        # source_url Fallback
        if not para.get('source_url'):
            fallback_idx = min(i, 2) # Local fallback for 3 paragraphs in one section
            if fallback_idx < source_count:
                para['source_url'] = labeled_sources[fallback_idx][0]
            elif source_count > 0:
                para['source_url'] = labeled_sources[0][0]

        keyword = para.get('image_search_keyword')
        para['image_url'] = None
        if keyword:
            try:
                imgs = search_with_pexels(keyword, orientation='landscape', per_page=1)
                if imgs: para['image_url'] = imgs[0]
            except: pass
        if not para['image_url'] and images: para['image_url'] = images[0]

    new_section['thumbnail_url'] = None
    try:
        imgs = search_with_pexels(new_section.get('heading', magazine_title), orientation='landscape', per_page=1)
        if imgs: new_section['thumbnail_url'] = imgs[0]
    except: pass
    if not new_section['thumbnail_url'] and images: new_section['thumbnail_url'] = images[0]
    
    # V2 Cleanup
    new_section.pop('subtitle', None)
    new_section.pop('introduction', None)
    
    # [Final Language Guard] Force translate if AI still returns English
    new_section = force_translate_section(new_section)
    
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

def generate_paragraph(topic: str, section_heading: str, message: str, user_mood: str, existing_paragraphs: list) -> dict:
    """
    섹션 맨 끝에 문단을 추가하기 위한 콘텐츠 생성
    """
    from app.core.searcher import search_with_tavily
    from app.core.llm_client import llm_client
    import json
    
    # 1. 주제 및 내용 기반 검색
    search_query = f"{topic} {section_heading} {message}"
    print(f"Searching for new paragraph: {search_query}")
    source_url = None
    try:
        search_results, images = search_with_tavily(search_query, topic=topic)
    except Exception as e:
        print(f"Search failed: {e}")
        search_results, images = [], []
        
    research_content = ""
    if search_results:
        source_url = search_results[0].get('url', None)
        research_content = "\n".join([f"- {r.get('title')}: {r.get('content')[:200]}" for r in search_results[:1]])
    
    # 2. 기존 문단 텍스트 추출 (중복 방지)
    existing_text = "\n".join([f"Subtitle: {p.get('subtitle')}\nText: {p.get('text')}" for p in existing_paragraphs])
    
    system_prompt = f"""
    You are an AI editor for a premium lifestyle magazine.
    Your task is to generate a NEW paragraph (subtitle, text, and image) to be appended to the current section.
    
    [MAGAZINE CONTEXT]
    Topic: {topic}
    Section Heading: {section_heading}
    Tone/Mood: {user_mood if user_mood else 'vibrant and sophisticated'}
    
    [EXISTING PARAGRAPHS in this section]
    {existing_text if existing_text else "None."}
    
    CRITICAL INSTRUCTIONS:
    1. Do NOT repeat what is already in the EXISTING PARAGRAPHS. Provide fresh information or a new perspective.
    2. Directly address the user's specific request: "{message}"
    3. Use the provided [Research Results] to add specific facts, numbers, or deep insights.
    4. Write in sophisticated, editorial Korean (합쇼체/해요체, ~습니다/~입니다).
    5. The 'text' should be a single continuous string in Markdown (NO HTML TAGS), with a length of 300-600 characters. Use **bold** or italics naturally.
    6. Generate a specific `image_search_keyword` in ENGLISH NOUNS ONLY (Max 3 words) optimized for Pexels stock photo search.
    
    Output JSON (snake_case) exactly like this:
    {{
        "subtitle": "...",
        "text": "The main content in Markdown format...",
        "image_search_keyword": "keyword",
        "source_url": "URL used for this content",
        "image_url": null
    }}
    """
    
    user_prompt = f"""
    User Request: {message}
    
    [Research Results]
    {research_content if research_content else "No research available."}
    
    [Available Images]
    {json.dumps(images[:5], ensure_ascii=False) if images else "[]"}
    """
    
    result = llm_client.generate_json(system_prompt, user_prompt, temperature=0.7)
    
    # Request Pexels for new paragraph image
    search_keyword = result.get('image_search_keyword', '')
    result['image_url'] = None
    
    if search_keyword:
        from app.core.searcher import search_with_pexels
        print(f"📸 generate_paragraph: Pexels search for '{search_keyword}'")
        try:
            pexels_imgs = search_with_pexels(search_keyword, orientation='landscape', per_page=1)
            if pexels_imgs:
                result['image_url'] = pexels_imgs[0]
                print(f"✅ Assigned Pexels image: {pexels_imgs[0]}")
        except Exception as e:
            print(f"⚠️ Pexels failed for generate_paragraph: {e}")
            
    # Fallback to Tavily
    if not result['image_url'] and images:
        result['image_url'] = images[0]
        print(f"Fallback to Tavily image: {images[0]}")
    
    # [One Source One Use] source_url 첨부
    if source_url:
        result['source_url'] = source_url
        
    return result


def strip_markdown_codeblocks(content: str) -> str:
    """
    LLM 출력에서 최외곽 마크다운 코드블럭을 제거합니다.
    예: ```markdown\n내용\n``` → 내용
    """
    if not content:
        return content
        
    import re
    
    # ```markdown ... ``` 또는 ``` ... ``` 패턴 제거
    pattern = r'^```(?:markdown|md|html|HTML)?\s*([\s\S]*?)\s*```$'
    match = re.search(pattern, content.strip())
    if match:
        return match.group(1).strip()
    
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
                _, images = search_with_tavily(message, topic=topic)
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
                "You are a magazine editor. Output Markdown content only. Include images using ![]() tags.",
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
                "You are a magazine editor. Output Markdown content only.",
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
                "You are a magazine editor. Output Markdown content only.",
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
                topic=topic,
                existing_content=original_content,
                message="간단하게, 짧게, 쉽게"
            )
            new_content = llm_client.generate_text(
                "You are a magazine editor. Output Markdown content only.",
                tone_prompt,
                temperature=0.6
            )
            
        elif intent == 'EXPAND':
            # 자세하게 (V2의 CHANGE_TONE 프롬프트 재사용)
            tone_prompt = CHANGE_TONE_PROMPT_V2.format(
                topic=topic,
                existing_content=original_content,
                message="더 자세하게, 길게, 깊이있게"
            )
            new_content = llm_client.generate_text(
                "You are a magazine editor. Output Markdown content only.",
                tone_prompt,
                temperature=0.7
            )
                
        else:
            # 기본: APPEND_CONTENT와 동일하게 처리
            from app.core.searcher import search_with_tavily
            import json
            
            print(f"🔍 Searching images for: {message[:30]}...")
            try:
                _, images = search_with_tavily(message, topic=topic)
                available_images = json.dumps(images[:5], ensure_ascii=False) if images else "[]"
            except Exception as e:
                print(f"⚠️ Image search failed: {e}")
                available_images = "[]"
            
            append_prompt = APPEND_CONTENT_PROMPT_V2.format(
                topic=topic,
                existing_content=original_content,
                message=message,
                available_images=available_images
            )
            new_content = llm_client.generate_text(
                "You are a magazine editor. Output Markdown content only. Include images using ![]() tags.",
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
    }# FORCE_SYNC_V3

# DEPLOY_VERSION: 17
