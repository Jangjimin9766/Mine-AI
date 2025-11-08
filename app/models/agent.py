from pydantic import BaseModel

class ChatRequest(BaseModel):
    """
    AI 에이전트 채팅 요청 모델
    """
    user_id: str  # 어떤 사용자의 요청인지 식별
    message: str  # 사용자가 입력한 메시지

class ChatResponse(BaseModel):
    """
    AI 에이전트 채팅 응답 모델
    """
    answer: str   # AI 에이전트의 답변