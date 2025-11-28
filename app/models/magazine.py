from pydantic import BaseModel
from typing import List, Optional

class MagazineSection(BaseModel):
    heading: str            # 소제목
    content: str            # 본문 내용
    image_url: Optional[str] = None # 들어갈 이미지 URL (없을 수도 있음)
    layout_hint: str = "basic" # 프론트에게 주는 힌트 (예: 'image_left', 'full_width')

class Magazine(BaseModel):
    title: str              # 매거진 전체 제목
    introduction: str       # 도입부 (에디터의 말)
    cover_image_url: str    # 표지 이미지
    sections: List[MagazineSection] # 본문 섹션들
    tags: List[str]         # 태그

class MagazineRequest(BaseModel):
    topic: str              # 주제 (예: "겨울 코트 추천")
    user_email: str         # 사용자 아이디 (Username) - Spring에서 보냄
    user_mood: Optional[str] = None # 사용자 취향 (선택)