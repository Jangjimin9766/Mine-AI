from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.magazine import Magazine, MagazineRequest
from app.core.magazine_maker import generate_magazine_content

router = APIRouter()

@router.post("/create", response_model=Magazine)
def create_magazine(request: MagazineRequest):
    """
    AI가 매거진을 생성하고, 완료되면 Spring 서버에 자동으로 저장합니다.
    """
    # 1. AI가 매거진 생성 (시간이 좀 걸림)
    magazine_data = generate_magazine_content(request.topic)
    
    if not magazine_data:
        raise HTTPException(status_code=500, detail="Failed to generate magazine")
    
    # Gateway 패턴 적용: Python은 생성된 데이터만 리턴하고, 저장은 Spring이 알아서 함.
    return magazine_data