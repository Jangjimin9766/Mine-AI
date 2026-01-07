# Mine-AI 향후 개선 사항

## 섹션 생성 로직 변경 가능성

**현재 상태:** 매거진 생성 시 AI가 4개 이상의 섹션을 자동 생성
**향후 옵션:** 사용자가 섹션을 직접 추가하는 방식으로 변경 가능

### 변경 방법
1. `app/core/prompts.py` - `MAGAZINE_SYSTEM_PROMPT_V3` 수정
   - "Generate at least 4 sections" → "Generate only 1 section"
2. `app/core/magazine_maker.py` - 필요 시 섹션 수 제한 로직 추가

### 관련 결정
- 2026-01-08: 현재는 여러 섹션 생성 유지 (사용자가 불필요한 섹션 삭제하는 방식)
- 추후 UX 테스트 후 변경 여부 결정

---

## 기타 메모
- `user_mood` 파라미터 지원 완료 (2026-01-08)
- HTML 태그 사용: `<h3>`, `<p>`, `<strong>`, `<ul>`, `<blockquote>`, `<br>`
