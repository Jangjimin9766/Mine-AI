# 팀 협업 가이드 (Team Collaboration Guide)

이 문서는 우리 팀이 효율적으로 협업하고 코드 품질을 유지하기 위해 따르는 작업 방식을 설명합니다.

## 1. 이슈(Issue) 관리 (작업 할당)
모든 작업(기능 개발, 버그 수정, 기타 업무)은 GitHub Issue를 생성하는 것부터 시작합니다.
- **제목(Title)**: 명확하고 간결하게 (예: "로그인 페이지 추가", "유저 API 500 에러 수정").
- **내용(Description)**: 요구사항, 작업 완료 조건, 에러 재현 방법 등을 상세히 적습니다.
- **담당자(Assignee)**: 작업을 수행할 사람(본인 또는 팀원)을 지정합니다.
- **라벨(Labels)**: `feature`, `bug`, `documentation` 등 성격에 맞는 라벨을 붙입니다.

## 2. 브랜치(Branch) 전략
우리는 **Feature Branch** 방식을 사용합니다.
- **메인 브랜치 (`main`)**: 언제든 배포 가능한 안정적인 상태여야 합니다. **직접 푸시가 금지되어 있습니다.**
- **작업 브랜치 (Feature Branches)**: `main`에서 따서 작업합니다.
    - **이름 규칙**: `feature/이슈번호-짧은설명` 또는 `fix/이슈번호-짧은설명`.
    - 예시: 이슈 #12 "로그인 추가" 작업 시 -> `feature/12-add-login`.
    - **생성 방법(팁)**: GitHub 이슈 페이지 오른쪽 사이드바 "Development" 섹션에서 "Create a branch"를 누르면 자동으로 연결되고 이름도 지어줍니다!

## 3. 개발 및 커밋 (Development & Commits)
- 커밋은 작게 자주 해주세요.
- **커밋 메시지**: 가능하다면 이슈 번호를 언급해주세요.
    - 예시: `feat: 로그인 폼 구현 (closes #12)`
    - **Conventional Commits** 규칙을 권장합니다 (feat, fix, docs, style, refactor, test, chore).

## 4. 풀 리퀘스트 (PR) 및 코드 리뷰
작업이 완료되면 다음 절차를 따릅니다:
1.  **Push**: 작업한 브랜치를 GitHub에 올립니다.
2.  **PR 생성 (Pull Request)**:
    - **Base**: `main` <- **Compare**: `feature/12-add-login`
    - **내용**: "Closes #12" 등을 적어 이슈와 연결하고, 변경 사항과 테스트 방법을 설명합니다.
3.  **자동 테스트 (CI)**:
    - PR이 올라오면 GitHub Actions가 자동으로 유닛 테스트를 실행합니다.
    - **모든 테스트를 통과(초록불)**해야만 병합할 수 있습니다.
4.  **코드 리뷰 (Code Review)**:
    - 팀원들에게 리뷰를 요청(Reviewers)합니다.
    - 리뷰어는 로직, 스타일, 버그 가능성 등을 체크합니다.
    - **팀원의 승인(Approve)**이 있어야 병합할 수 있습니다.
5.  **병합 (Merge)**:
    - 승인을 받고 테스트도 통과했다면, "Squash and merge" (이력 깔끔하게 유지) 또는 "Merge pull request"를 눌러 합칩니다.

## 5. 브랜치 보호 규칙 (Branch Protection Rules)
(저장소 설정이 완료되어 있어야 합니다)
- **Settings -> Branches** 메뉴에서 설정
- **Branch name pattern**: `main`
- [x] **Require a pull request before merging** (PR 필수)
- [x] **Require approvals** (팀원 승인 필수)
- [x] **Require status checks to pass before merging** (테스트 통과 필수)
