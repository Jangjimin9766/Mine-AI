from openai import OpenAI
from app.config import settings
from app.models.agent import ChatRequest

# OpenAI 클라이언트 초기화 (정상 작동)
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def get_llm_summary(text: str) -> str:
    """
    LLM을 사용하여 텍스트를 요약합니다. (간단 예시)
    """
    print(f"Requesting summary from LLM for text length: {len(text)}")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a fashion editor. Summarize this fashion article concisely."},
                {"role": "user", "content": text}
            ],
            temperature=0.7,
            max_tokens=150
        )
        summary = response.choices[0].message.content
        return summary.strip() if summary else "No summary generated."
    
    except Exception as e:
        print(f"Error during LLM API call: {e}")
        return "Error: Could not generate summary."

def get_agent_response(request: ChatRequest, user_data: dict) -> str:
    """
    사용자 데이터와 채팅 메시지를 기반으로 AI 에이전트 응답 생성
    """
    print(f"Generating agent response for user {request.user_id}...")
    
    # 1. user_data와 request.message를 조합하여 프롬프트 생성
    prompt = f"""
    You are 'M:ine', a personal fashion magazine AI agent.
    Your user's current collection data: {user_data}
    User's request: {request.message}
    
    Provide a helpful and stylish response:
    """
    
    # 2. [수정됨] 실제 LLM을 호출하여 답변 생성
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # 또는 gpt-4
            messages=[
                # 시스템 역할(프롬프트)과 사용자 메시지를 함께 전달
                {"role": "system", "content": prompt},
                {"role": "user", "content": request.message} # (프롬프트에 이미 포함했다면 이 줄은 빼도 됨)
            ],
            temperature=0.7,
            max_tokens=300 # 답변이 길 수 있으니 넉넉하게
        )
        ai_answer = response.choices[0].message.content
        return ai_answer.strip() if ai_answer else "No response generated."

    except Exception as e:
        print(f"Error during Agent LLM API call: {e}")
        return "Error: Could not generate agent response."