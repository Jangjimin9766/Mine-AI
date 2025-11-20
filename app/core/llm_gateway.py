from app.models.agent import ChatRequest
from app.core.llm_client import llm_client # [변경] 우리가 만든 클라이언트 임포트
import json

def get_llm_summary(text: str) -> str:
    """
    텍스트 요약
    """
    if not text: return ""
    print(f"🧠 AI Summarizing text (length: {len(text)})...")
    
    system_prompt = "You are a professional fashion editor. Summarize the following fashion article in Korean within 3 sentences. Focus on key trends and items."
    
    # [변경] 직접 호출 -> llm_client 사용
    return llm_client.generate_text(system_prompt, text, temperature=0.5)

def get_tags_from_text(text: str) -> list:
    """
    태그 추출
    """
    if not text: return []
    print(f"🏷️ AI Tagging text...")

    system_prompt = """
    Analyze the following fashion text and extract relevant tags.
    Categories: Style (e.g., Minimal, Vintage), Mood (e.g., Chic, Cozy), Item (e.g., Coat, Boots).
    Output format: A simple Python list of strings in Korean. Example: ["미니멀", "시크", "롱코트"]
    Do not write anything else, just the list.
    """
    
    # [변경] llm_client 사용
    result_text = llm_client.generate_text(system_prompt, text, temperature=0.3)
    
    try:
        if "[" in result_text and "]" in result_text:
            return eval(result_text)
        else:
            return result_text.split(",")
    except:
        return []

def get_agent_response(request: ChatRequest, data: dict) -> str:
    """
    AI 에이전트 채팅
    """
    print(f"💬 AI Agent thinking for user {request.user_id}...")

    system_prompt = """
    You are 'M:ine', a professional and trendy personal fashion curator.
    
    [Your Role]
    - Analyze the provided data (search results or user collection) and the question.
    - Recommend styles or items that fit the context.
    - Speak in a friendly, stylish tone (Korean).
    - Use emojis occasionally to keep it lively.
    
    [Context Data]
    {data}
    """
    
    formatted_system = system_prompt.format(data=json.dumps(data, ensure_ascii=False))
    
    # [변경] llm_client 사용
    return llm_client.generate_text(formatted_system, request.message, temperature=0.7)