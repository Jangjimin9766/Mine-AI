from fastapi import APIRouter
from app.models.agent import ChatRequest, ChatResponse
# from app.core.spring_client import get_user_data_from_spring # 잠시 주석 처리
from app.core.llm_gateway import get_agent_response

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def handle_chat_request(request: ChatRequest):
    
    # 1. [TEST] Spring 서버 대신 가짜 데이터 사용
    # 나중에는 실제 DB에서 가져온 데이터가 들어갈 자리입니다.
    user_data = {
        "preferred_styles": ["Minimal", "City Boy"],
        "recent_items": ["Wide Slacks", "White Shirt", "New Balance 993"],
        "mood": "Calm & Clean"
    }
    # user_data = get_user_data_from_spring(request.user_id) # 나중에 주석 해제

    # 2. AI 에이전트에게 질문
    ai_answer = get_agent_response(request, user_data)
    
    return ChatResponse(answer=ai_answer)