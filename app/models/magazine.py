from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class MoodboardResponse(BaseModel):
    image_url: str
    description: str

class MagazineSection(BaseModel):
    heading: str            # 소제목
    content: str            # 본문 내용 (HTML 태그 포함 가능)
    image_url: Optional[str] = None # 들어갈 이미지 URL (없을 수도 있음)
    layout_type: str = "basic" # 프론트엔드 렌더링 힌트 (예: 'hero', 'quote', 'split_left', 'split_right')
    layout_hint: Optional[str] = None # 추가 레이아웃 힌트 (예: 'image_left', 'full_width')
    caption: Optional[str] = None # 이미지 캡션 (선택)
    display_order: Optional[int] = None # 그리드 내 표시 순서

class Magazine(BaseModel):
    title: str              # 매거진 전체 제목
    subtitle: str           # 사용자의 흥미를 끄는 부제
    introduction: str       # 도입부 (에디터의 말)
    cover_image_url: str    # 표지 이미지
    sections: List[MagazineSection] # 본문 섹션들
    tags: List[str]         # 태그
    moodboard: Optional[MoodboardResponse] = None # 매거진과 1:1 매칭되는 무드보드

class MagazineRequest(BaseModel):
    """Legacy request model for create_magazine only"""
    topic: str              # 주제 (예: "겨울 코트 추천", "제주도 여행", "건강한 아침 식단")
    user_email: str         # 사용자 아이디 (Username) - Spring에서 보냄
    user_mood: Optional[str] = None # 사용자 취향 (선택)
    user_interests: Optional[List[str]] = None # 사용자 관심사 (예: ["여행", "음악", "건강"])

class MoodboardRequest(BaseModel):
    topic: Optional[str] = None
    user_mood: Optional[str] = None
    user_interests: Optional[List[str]] = None
    magazine_tags: Optional[List[str]] = None
    magazine_titles: Optional[List[str]] = None

# ==========================================
# 통합 요청 모델 (Action 기반)
# ==========================================

class UnifiedMagazineRequest(BaseModel):
    """
    Spring에서 보내는 모든 요청을 처리하는 통합 모델.
    action에 따라 필요한 필드가 다름.
    """
    action: str  # "create_magazine", "edit_magazine", "edit_section"
    
    # create_magazine용
    topic: Optional[str] = None
    user_email: Optional[str] = None
    user_mood: Optional[str] = None
    user_interests: Optional[List[str]] = None
    
    # edit_magazine용
    magazine_id: Optional[int] = None
    magazine_data: Optional[Dict[str, Any]] = None
    
    # edit_section용
    section_id: Optional[int] = None
    section_data: Optional[Dict[str, Any]] = None
    
    # 공통
    message: Optional[str] = None  # 사용자 요청 메시지