import json
from app.core.llm_client import llm_client
from app.core.searcher import search_with_tavily, scrape_with_jina

def generate_magazine_content(topic: str):
    print(f"🎨 Magazine Editor started for: {topic}")

    # 1. [취재] Tavily로 정보와 이미지 수집
    search_results, images = search_with_tavily(topic)
    
    # 2. [정독] 상위 1개 글 정독 (Jina)
    deep_content = ""
    if search_results:
        deep_content = scrape_with_jina(search_results[0]['url'])
        if not deep_content:
            deep_content = search_results[0]['content']

    # 3. [편집] LLM에게 매거진 작성 요청
    
    system_prompt = """
    You are the Editor-in-Chief of 'M:ine', a high-end fashion magazine.
    Create a magazine article based on the provided context.
    
    [CRITICAL INSTRUCTION]
    1. You MUST output ONLY a valid JSON object.
    2. **ALL content (titles, descriptions, tags) MUST be written in KOREAN.** (한국어로 작성)
    3. Do not use English unless it is a brand name or proper noun.
    
    Structure the JSON as follows:
    {
        "title": "Catchy Main Title (in Korean)",
        "introduction": "Short intro paragraph (in Korean)",
        "cover_image_url": "Pick one URL from the provided image list",
        "tags": ["tag1", "tag2"],
        "sections": [
            {
                "heading": "Subheading (in Korean)",
                "content": "Detailed paragraph (~200 chars, in Korean)",
                "image_url": "Pick a DIFFERENT URL from the list if available",
                "layout_hint": "image_left" or "full_width"
            }
        ]
    }
    """

    user_prompt = f"""
    Topic: {topic}
    
    [Source Content]
    {deep_content[:3000]}
    
    [Available Image URLs]
    {json.dumps(images)}
    """

    print("🧠 AI Layout & Drafting (in Korean)...")
    
    # llm_client 사용
    result_json = llm_client.generate_json(system_prompt, user_prompt, temperature=0.7)
    
    return result_json