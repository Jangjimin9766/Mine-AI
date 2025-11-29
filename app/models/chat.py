from pydantic import BaseModel
from typing import Optional, Dict, Any

class MagazineChatRequest(BaseModel):
    magazine_id: int
    magazine_data: Dict[str, Any]  # 현재 매거진 전체 데이터
    user_message: str              # 사용자 메시지 (예: "첫 번째 섹션을 더 감성적으로")

class AgentIntent(BaseModel):
    action: str                    # "regenerate_section", "add_section", etc.
    target_section_index: Optional[int] = None
    instruction: str               # AI가 이해한 구체적 지시사항
    response_message: str          # 사용자에게 보여줄 응답

class MagazineChatResponse(BaseModel):
    action: str
    section_index: Optional[int] = None
    new_section: Optional[Dict[str, Any]] = None
    new_sections: Optional[list] = None  # 전체 섹션 재생성 시
    message: str
