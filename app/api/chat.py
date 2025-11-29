from fastapi import APIRouter, HTTPException
from app.models.chat import MagazineChatRequest, MagazineChatResponse
from app.core.magazine_editor import (
    analyze_user_intent,
    regenerate_section,
    add_new_section,
    change_overall_tone
)

router = APIRouter()

@router.post("/chat", response_model=MagazineChatResponse)
def chat_with_magazine(request: MagazineChatRequest):
    """
    매거진 내에서 AI 에이전트와 대화하며 내용 수정
    """
    try:
        # 1. 사용자 의도 분석
        intent = analyze_user_intent(request.user_message, request.magazine_data)
        
        # 2. 액션 수행
        if intent.action == "regenerate_section":
            new_section = regenerate_section(
                magazine_data=request.magazine_data,
                section_index=intent.target_section_index,
                instruction=intent.instruction
            )
            return MagazineChatResponse(
                action="regenerate_section",
                section_index=intent.target_section_index,
                new_section=new_section,
                message=intent.response_message
            )
        
        elif intent.action == "add_section":
            new_section = add_new_section(
                magazine_data=request.magazine_data,
                instruction=intent.instruction
            )
            return MagazineChatResponse(
                action="add_section",
                new_section=new_section,
                message=intent.response_message
            )
        
        elif intent.action == "change_tone":
            new_sections = change_overall_tone(
                magazine_data=request.magazine_data,
                instruction=intent.instruction
            )
            return MagazineChatResponse(
                action="change_tone",
                new_sections=new_sections,
                message=intent.response_message
            )
        
        elif intent.action == "delete_section":
            return MagazineChatResponse(
                action="delete_section",
                section_index=intent.target_section_index,
                message=intent.response_message
            )
        
        else:
            return MagazineChatResponse(
                action="general_chat",
                message="죄송합니다. 아직 지원하지 않는 기능입니다."
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process request: {str(e)}")
