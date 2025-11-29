from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.magazine import Magazine, MagazineRequest, MoodboardRequest, MoodboardResponse
from app.core.magazine_maker import generate_magazine_content

router = APIRouter()

@router.post("/create", response_model=Magazine)
def create_magazine(request: MagazineRequest):
    """
    AI가 매거진을 생성합니다. (모든 주제 지원: 패션, 여행, 음악, 건강 등)
    """
    # 1. AI가 매거진 생성 (시간이 좀 걸림)
    magazine_data = generate_magazine_content(
        topic=request.topic,
        user_interests=request.user_interests
    )
    
    if not magazine_data:
        raise HTTPException(status_code=500, detail="Failed to generate magazine")
    
    # Gateway 패턴 적용: Python은 생성된 데이터만 리턴하고, 저장은 Spring이 알아서 함.
    return magazine_data

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