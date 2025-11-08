from pydantic import BaseModel
from typing import List

class SummarizeRequest(BaseModel):
    """
    텍스트 요약 요청 모델
    """
    text: str # 요약할 원본 텍스트

class SummarizeResponse(BaseModel):
    """
    텍스트 요약 응답 모델
    """
    summary: str # AI가 생성한 요약문

# (향후 태깅 기능 추가 시)
# class TaggingResponse(BaseModel):
#     tags: List[str]