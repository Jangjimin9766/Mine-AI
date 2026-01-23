from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.magazine import Magazine, MagazineRequest, MoodboardRequest, MoodboardResponse, UnifiedMagazineRequest
from app.core.magazine_maker import generate_magazine_content

router = APIRouter()

@router.post("/create")
def handle_magazine_request(request: UnifiedMagazineRequest):
    """
    통합 매거진 API 엔드포인트.
    action에 따라 다른 처리:
    - create_magazine: 새 매거진 생성
    - edit_magazine: 매거진 레벨 수정 (섹션 추가/삭제)
    - edit_section: 특정 섹션 수정
    """
    action = request.action
    
    if action == "create_magazine":
        return handle_create_magazine(request)
    elif action == "edit_magazine":
        return handle_edit_magazine(request)
    elif action == "edit_section":
        return handle_edit_section(request)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


def handle_create_magazine(request: UnifiedMagazineRequest):
    """매거진 생성"""
    print(f"🚀 [Python] handle_create_magazine started for topic: {request.topic}")
    if not request.topic:
        raise HTTPException(status_code=400, detail="topic is required for create_magazine")
    
    try:
        magazine_data = generate_magazine_content(
            topic=request.topic,
            user_interests=request.user_interests,
            user_mood=request.user_mood
        )
        
        if not magazine_data:
            print("❌ [Python] generate_magazine_content returned None")
            raise HTTPException(status_code=500, detail="Failed to generate magazine")
        
        print(f"✅ [Python] Magazine generated successfully. Title: {magazine_data.get('title')}")
        return magazine_data
    except Exception as e:
        print(f"❌ [Python] Exception in handle_create_magazine: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def handle_edit_magazine(request: UnifiedMagazineRequest):
    """매거진 레벨 수정 (섹션 추가/삭제)"""
    from app.core.magazine_editor import (
        analyze_user_intent,
        regenerate_section,
        add_new_section,
        change_overall_tone
    )
    
    if not request.message:
        raise HTTPException(status_code=400, detail="message is required for edit_magazine")
    if not request.magazine_data:
        raise HTTPException(status_code=400, detail="magazine_data is required for edit_magazine")
    
    try:
        intent = analyze_user_intent(request.message, request.magazine_data)
        
        result = None
        new_sections = []
        deleted_section_ids = []
        
        if intent.action == "regenerate_section":
            result = regenerate_section(
                request.magazine_data,
                intent.target_section_index,
                intent.instruction
            )
            new_sections = [result] if result else []
        elif intent.action == "add_section":
            result = add_new_section(request.magazine_data, intent.instruction)
            new_sections = [result] if result else []
        elif intent.action == "delete_section":
            if intent.target_section_index is not None:
                sections = request.magazine_data.get('sections', [])
                if 0 <= intent.target_section_index < len(sections):
                    deleted_section_ids = [sections[intent.target_section_index].get('id')]
        elif intent.action == "change_tone":
            result = change_overall_tone(request.magazine_data, intent.instruction)
            new_sections = result if isinstance(result, list) else []
        else:
            result = change_overall_tone(request.magazine_data, request.message)
            new_sections = result if isinstance(result, list) else []
        
        return {
            "intent": intent.action if intent else "no_change",
            "success": True,
            "updated_magazine": {
                "heading": intent.response_message if intent else "수정이 완료되었습니다",
                "new_sections": new_sections,
                "deleted_section_ids": deleted_section_ids
            }
        }
    except Exception as e:
        return {
            "intent": "no_change",
            "success": False,
            "error": str(e),
            "updated_magazine": None
        }


def handle_edit_section(request: UnifiedMagazineRequest):
    """특정 섹션 수정"""
    from app.core.magazine_editor import edit_section_content
    
    if not request.message:
        raise HTTPException(status_code=400, detail="message is required for edit_section")
    if not request.section_data:
        raise HTTPException(status_code=400, detail="section_data is required for edit_section")
    
    try:
        # 잡지 데이터에서 주제 추출
        topic = request.section_data.get('magazine_title') or request.topic or "Magazine Content"
        result = edit_section_content(request.section_data, request.message, topic=topic)
        return result
    except Exception as e:
        return {
            "intent": "modify_content",
            "success": False,
            "error": str(e),
            "updated_section": None
        }


@router.post("/moodboard", response_model=MoodboardResponse)
def create_moodboard(request: MoodboardRequest):
    """
    주제와 사용자 취향을 기반으로 무드보드 이미지를 생성합니다.
    """
    from app.core.moodboard_maker import generate_moodboard
    from app.models.magazine import MoodboardResponse

    result = generate_moodboard(
        topic=request.topic,
        user_mood=request.user_mood,
        user_interests=request.user_interests,
        magazine_tags=request.magazine_tags,
        magazine_titles=request.magazine_titles
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate moodboard")

    return MoodboardResponse(**result)