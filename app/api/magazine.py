from fastapi import APIRouter, HTTPException
from app.models.magazine import Magazine, MagazineRequest
from app.core.magazine_maker import generate_magazine_content

router = APIRouter()

@router.post("/create", response_model=Magazine)
def create_magazine(request: MagazineRequest):
    """
    주제를 입력받아 AI가 기획, 집필, 디자인한 매거진 데이터를 생성합니다.
    """
    magazine_data = generate_magazine_content(request.topic)
    
    if not magazine_data:
        raise HTTPException(status_code=500, detail="Failed to generate magazine")
    
    return magazine_data