from fastapi import APIRouter, HTTPException

from app.config import settings
from app.core.magazine_maker import generate_magazine_content
from app.models.magazine import MoodboardRequest, MoodboardResponse, UnifiedMagazineRequest

router = APIRouter()


def build_mock_magazine(topic: str, user_interests=None, user_mood: str = ""):
    interests = user_interests or ["LIFESTYLE"]
    interest_line = ", ".join(interests[:3])
    cover = "https://images.unsplash.com/photo-1571019613540-9960a0cf11c4?w=1200"

    return {
        "title": f"균형의 공간, {topic}",
        "subtitle": f"{interest_line} 관점으로 풀어낸 {topic} 가이드",
        "introduction": (
            f"{topic}을 처음 접하는 사람도 흐름을 따라갈 수 있도록 공간, 루틴, 지속 가능성 "
            "관점에서 정리한 로컬 QA용 매거진입니다."
        ),
        "cover_image_url": cover,
        "tags": [topic, "QA", "LOCAL", "WELLNESS", "GUIDE"],
        "sections": [
            {
                "heading": f"{topic}의 첫인상",
                "thumbnail_url": cover,
                "layout_type": "hero",
                "layout_hint": "zigzag",
                "display_order": 0,
                "paragraphs": [
                    {
                        "subtitle": "공간의 분위기",
                        "text": (
                            f"{topic}은 첫인상에서 진입장벽이 갈립니다. 로컬 QA 응답에서는 "
                            "사용자가 어떤 감정으로 들어와도 핵심 정보를 빠르게 파악할 수 있도록 "
                            "공간감과 흐름을 먼저 설명합니다."
                        ),
                        "image_url": cover,
                    },
                    {
                        "subtitle": "기본 루틴의 구조",
                        "text": (
                            f"{topic}의 정보는 복잡해 보일 수 있지만, 실제로는 준비 단계와 실행 단계, "
                            "마무리 단계로 나누면 훨씬 이해하기 쉽습니다. 이 구조는 테스트 중 "
                            "결과물 검증에도 유리합니다."
                        ),
                        "image_url": cover,
                    },
                    {
                        "subtitle": "초보자 관점",
                        "text": (
                            f"처음 {topic}을 접하는 사용자에게는 전문성보다도 부담 없이 시작할 수 있는 "
                            "흐름이 중요합니다. 그래서 문단은 짧고 명확하게, 화면에서 읽기 쉽게 "
                            "구성됩니다."
                        ),
                        "image_url": cover,
                    },
                ],
            },
            {
                "heading": f"{topic}을 지속하는 방법",
                "thumbnail_url": cover,
                "layout_type": "split_left",
                "layout_hint": "zigzag",
                "display_order": 1,
                "paragraphs": [
                    {
                        "subtitle": "작게 시작하기",
                        "text": (
                            f"{topic}은 한 번에 완벽하게 하려 할수록 오래가기 어렵습니다. "
                            "작은 반복을 기준으로 습관을 설계하면 실제 사용성도 자연스럽게 올라갑니다."
                        ),
                        "image_url": cover,
                    },
                    {
                        "subtitle": "관심사와 연결하기",
                        "text": (
                            f"이 응답은 사용자의 관심사인 {interest_line}을 엮어 설명합니다. "
                            "개인 관심사와 연결된 콘텐츠는 정보 전달력뿐 아니라 체감 만족도도 높여줍니다."
                        ),
                        "image_url": cover,
                    },
                    {
                        "subtitle": "기록과 회고",
                        "text": (
                            f"{topic}을 오래 유지하려면 결과보다 기록이 중요합니다. 무엇이 쉬웠고 "
                            "어려웠는지 남기면 다음 행동이 선명해지고, 서비스도 더 명확한 피드백을 "
                            "받을 수 있습니다."
                        ),
                        "image_url": cover,
                    },
                ],
            },
        ],
    }


@router.post("/create")
def handle_magazine_request(request: UnifiedMagazineRequest):
    action = request.action

    if action == "create_magazine":
        return handle_create_magazine(request)
    if action == "edit_magazine":
        return handle_edit_magazine(request)
    if action == "edit_section":
        return handle_edit_section(request)

    raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


def handle_create_magazine(request: UnifiedMagazineRequest):
    print(f"[Python] handle_create_magazine started for topic: {request.topic}")
    if not request.topic:
        raise HTTPException(status_code=400, detail="topic is required for create_magazine")

    if settings.LOCAL_QA_MOCK_MODE:
        print("[Python] LOCAL_QA_MOCK_MODE enabled, returning mock magazine")
        return build_mock_magazine(
            topic=request.topic,
            user_interests=request.user_interests,
            user_mood=request.user_mood or "",
        )

    try:
        magazine_data = generate_magazine_content(
            topic=request.topic,
            user_interests=request.user_interests,
            user_mood=request.user_mood,
        )

        if not magazine_data:
            print("[Python] generate_magazine_content returned None")
            raise HTTPException(status_code=500, detail="Failed to generate magazine")

        print(f"[Python] Magazine generated successfully. Title: {magazine_data.get('title')}")
        return magazine_data
    except Exception as e:
        print(f"[Python] Exception in handle_create_magazine: {str(e)}")
        import traceback

        traceback.print_exc()
        if settings.LOCAL_QA_MOCK_MODE:
            print("[Python] Falling back to mock magazine after exception")
            return build_mock_magazine(
                topic=request.topic,
                user_interests=request.user_interests,
                user_mood=request.user_mood or "",
            )
        raise HTTPException(status_code=500, detail=str(e))


def handle_edit_magazine(request: UnifiedMagazineRequest):
    from app.core.magazine_editor import (
        add_new_section,
        analyze_user_intent,
        change_overall_tone,
        regenerate_section,
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
                intent.instruction,
            )
            new_sections = [result] if result else []
        elif intent.action == "add_section":
            result = add_new_section(request.magazine_data, intent.instruction)
            new_sections = [result] if result else []
        elif intent.action == "delete_section":
            if intent.target_section_index is not None:
                sections = request.magazine_data.get("sections", [])
                if 0 <= intent.target_section_index < len(sections):
                    deleted_section_ids = [sections[intent.target_section_index].get("id")]
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
                "heading": intent.response_message if intent else "수정이 완료되었습니다.",
                "new_sections": new_sections,
                "deleted_section_ids": deleted_section_ids,
            },
        }
    except Exception as e:
        return {
            "intent": "no_change",
            "success": False,
            "error": str(e),
            "updated_magazine": None,
        }


def handle_edit_section(request: UnifiedMagazineRequest):
    from app.core.magazine_editor import edit_section_content

    if not request.message:
        raise HTTPException(status_code=400, detail="message is required for edit_section")
    if not request.section_data:
        raise HTTPException(status_code=400, detail="section_data is required for edit_section")

    try:
        topic = request.section_data.get("magazine_title") or request.topic or "Magazine Content"
        result = edit_section_content(request.section_data, request.message, topic=topic)
        return result
    except Exception as e:
        return {
            "intent": "modify_content",
            "success": False,
            "error": str(e),
            "updated_section": None,
        }


@router.post("/moodboard", response_model=MoodboardResponse)
def create_moodboard(request: MoodboardRequest):
    from app.core.moodboard_maker import generate_moodboard
    from app.models.magazine import MoodboardResponse

    result = generate_moodboard(
        topic=request.topic,
        user_mood=request.user_mood,
        user_interests=request.user_interests,
        magazine_tags=request.magazine_tags,
        magazine_titles=request.magazine_titles,
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate moodboard")

    return MoodboardResponse(**result)
