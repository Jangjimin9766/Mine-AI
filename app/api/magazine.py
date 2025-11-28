from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models.magazine import Magazine, MagazineRequest
from app.core.magazine_maker import generate_magazine_content
# [추가] 저장 함수 임포트 (이 부분이 핵심입니다)
from app.core.spring_client import save_magazine_to_spring

router = APIRouter()

@router.post("/create", response_model=Magazine)
def create_magazine(request: MagazineRequest, background_tasks: BackgroundTasks):
    """
    AI가 매거진을 생성하고, 완료되면 Spring 서버에 자동으로 저장합니다.
    """
    # 1. AI가 매거진 생성 (시간이 좀 걸림)
    magazine_data = generate_magazine_content(request.topic)
    
    if not magazine_data:
        raise HTTPException(status_code=500, detail="Failed to generate magazine")
    
    # 2. [핵심] Spring 서버로 전송 (백그라운드 작업으로 처리)
    # 사용자는 AI 결과를 바로 보고, 저장은 뒤에서 조용히 수행됨 (응답 속도 저하 없음)
    background_tasks.add_task(save_magazine_to_spring, magazine_data, request.user_email)
    
    return magazine_data