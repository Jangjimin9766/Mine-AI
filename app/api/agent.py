from fastapi import APIRouter
from app.models.agent import ChatRequest, ChatResponse
from app.core.spring_client import get_user_data_from_spring
# [수정] 클래스가 아닌 함수를 임포트
from app.core.llm_gateway import get_agent_response 

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def handle_chat_request(request: ChatRequest):
    """
    사용자의 채팅 메시지를 받아 AI 에이전트가 답변을 생성합니다.
    """
    
    # 1. Spring 서버에서 사용자 데이터 가져오기
    user_data = get_user_data_from_spring(request.user_id)
    
    # 2. [수정] 임포트한 함수를 바로 호출
    ai_answer = get_agent_response(request, user_data)
    
    return ChatResponse(answer=ai_answer)