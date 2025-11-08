from fastapi import APIRouter
# [수정] 모델 파일(analysis.py)에 정의된 이름으로 변경
from app.models.analysis import SummarizeRequest, SummarizeResponse 
from app.core.llm_gateway import get_llm_summary

router = APIRouter()

@router.post("/summarize", response_model=SummarizeResponse)
# [수정] 파라미터 타입도 변경
def api_summarize_text(request: SummarizeRequest): 
    """
    입력된 텍스트를 AI를 통해 요약합니다.
    """
    summary_text = get_llm_summary(request.text)
    
    return SummarizeResponse(summary=summary_text)