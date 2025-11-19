from openai import OpenAI
from app.config import settings
from app.models.agent import ChatRequest
import json

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def get_llm_summary(text: str) -> str:
    """
    LLM을 사용하여 텍스트를 3줄 내외로 요약합니다.
    """
    if not text: return ""
    print(f"🧠 AI Summarizing text (length: {len(text)})...")
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional fashion editor. Summarize the following fashion article in Korean within 3 sentences. Focus on key trends and items."},
                {"role": "user", "content": text}
            ],
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Error during Summary: {e}")
        return "요약 실패"

def get_tags_from_text(text: str) -> list:
    """
    텍스트에서 패션 스타일, 무드, 아이템 관련 태그를 추출합니다.
    """
    if not text: return []
    print(f"🏷️ AI Tagging text...")

    prompt = """
    Analyze the following fashion text and extract relevant tags.
    Categories: Style (e.g., Minimal, Vintage), Mood (e.g., Chic, Cozy), Item (e.g., Coat, Boots).
    Output format: A simple Python list of strings in Korean. Example: ["미니멀", "시크", "롱코트"]
    Do not write anything else, just the list.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
        )
        content = response.choices[0].message.content.strip()
        
        # 문자열을 리스트로 변환 (안전 장치)
        if "[" in content and "]" in content:
            return eval(content) 
        else:
            return content.split(",") 
            
    except Exception as e:
        print(f"❌ Error during Tagging: {e}")
        return []

def get_agent_response(request: ChatRequest, user_data: dict) -> str:
    """
    [AI 에이전트] 사용자의 데이터와 질문을 바탕으로 맞춤형 답변을 생성합니다.
    """
    print(f"💬 AI Agent thinking for user {request.user_id}...")

    # 1. 에이전트 페르소나 정의 (프롬프트 엔지니어링)
    system_prompt = """
    You are 'M:ine', a professional and trendy personal fashion curator.
    
    [Your Role]
    - Analyze the user's collection data and question.
    - Recommend styles or items that fit the user's taste.
    - Speak in a friendly, stylish tone (Korean).
    - Use emojis occasionally to keep it lively.
    
    [User Data]
    This is what the user likes (Collections):
    {user_data}
    """
    
    # user_data가 딕셔너리라면 문자열로 변환
    formatted_prompt = system_prompt.format(user_data=json.dumps(user_data, ensure_ascii=False))

    try:
        # 2. LLM에게 질문
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": request.message}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        ai_answer = response.choices[0].message.content.strip()
        return ai_answer

    except Exception as e:
        print(f"❌ Error during Agent Chat: {e}")
        return "죄송해요, 지금은 패션 영감을 떠올리기 힘드네요. 잠시 후 다시 말을 걸어주세요! 💦"