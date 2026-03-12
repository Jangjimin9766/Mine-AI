# CIJ_ASSIGNMENT_260313 

## 1) 이번 작업에서 **완료된 범위**
- 매거진 생성 프롬프트를 HTML 중심에서 **Markdown 중심**으로 전환했습니다.
  - 문단 `text` 필드가 Markdown을 사용하도록 명시
  - `>`, `-`/`1.`, `**bold**` 스타일 가이드 추가
  - 기존 핵심 제약(3문단, 600~800자, 태그 whitelist, 이미지 키워드 규칙)은 유지
- 생성 오케스트레이터(`magazine_maker`)의 사용자 프롬프트도 Markdown 지침으로 맞췄습니다.
- 신규 유저 피드 초기화를 위해 **5명 × 3개 = 총 15개 매거진** 자동 생성 스크립트를 추가했습니다.
  - 결과 JSON 파일 저장
  - 선택적으로 Mine-server 내부 벌크 API 업로드 지원

## 2) 내용

1. **PR 제목/요약**
   - "매거진 본문 Markdown 전환 + 초기 더미 15건 생성 스크립트 추가"
2. **변경 파일 목록**
   - `app/core/prompts.py`
   - `app/core/magazine_maker.py`
   - `app/models/magazine.py`
   - `tools/generate_initial_dummy_data.py`
3. **실행 방법(더미 생성)**
   - `python tools/generate_initial_dummy_data.py`
   - 선택: `MINE_SERVER_BULK_URL`, `MINE_SERVER_BEARER_TOKEN` 설정 시 Mine-server 업로드까지 수행
4. **리스크/후속작업 한 줄**
   - "프론트 Markdown 렌더러 반영 후 화면 QA 필요"


