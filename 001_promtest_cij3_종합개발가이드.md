# 001_promtest_cij3_종합개발가이드 (2026 CIJ3 Ver.)

이 가이드는 CIJ3 프로젝트 환경에서 **데스크탑과 노트북을 오가며 매끄럽게 개발**하고, **V7급 하이엔드 매거진**을 생성하기 위해 필요한 모든 과정을 담고 있습니다.

---

## 🏗️ 1. 개발 전 준비: Git 동기화 (노트북 ↔ 데스크탑)

작업 장소를 옮길 때마다 가장 먼저 해야 하는 필수 과정입니다.

### A. 작업 마무리 시 (데스크탑/노트북 공통)
```bash
# 1. 현재 브랜치 확인
git branch

# 2. 모든 변경사항 저장 및 커밋
git add .
git commit -m "feat: CIJ3 [작업내용 요약]"

# 3. 서버(GitHub)에 업로드
git push origin [내-작업-브랜치]
```

### B. 새로운 환경에서 작업 시작 시 (노트북 등)
```bash
# 1. 서버의 최신 정보 가져오기
git fetch origin

# 2. 작업하던 브랜치로 이동 (또는 새로 가져오기)
git checkout [내-작업-브랜치]

# 3. 서버의 최신 코드를 내 노트북에 합치기
git pull origin [내-작업-브랜치]
```

---

## 🚀 2. 서버 실행 및 필수 미들이어

매거진 생성을 위해서는 API 서버뿐만 아니라 데이터 저장소(Redis)가 반드시 켜져 있어야 합니다.

### A. 미들웨어 실행 (Docker 활용)
```bash
# Redis 실행 (매거진 임시 저장 및 큐 관리용)
docker run -d -p 6379:6379 redis
```

### B. Python 서버 실행 (Mine-AI)
```bash
cd c:/Dev/workspace/project/Mine/Mine-AI

# 1. 가상환경 활성화 (Git Bash/Bash 기준)
source venv/Scripts/activate

# 2. 서버 실행
python -m app.main
```

### C. Spring Boot 서버 실행 (Mine_server)
```bash
cd c:/Dev/workspace/project/Mine/Mine_server

# Gradle을 통한 서버 실행
./gradlew bootRun
```

---

## 🧠 3. CIJ3 V7 매거진 생성 로직 (피드백 반영)

최신 CIJ3 버전에서는 **장지민 님**의 피드백을 반영하여 다음과 같은 하이엔드 로직이 적용되었습니다.

### 🎨 레이아웃 큐레이션 (Layout Alternating)
- **Hero**: 첫 섹션은 항상 풀사이즈 임팩트를 주는 `hero` 레이아웃으로 시작합니다.
- **Alternating**: 이후 섹션들은 시각적 리듬을 위해 `split_left`와 `split_right`가 지그재그(Alternating)로 자동 배치됩니다.

### 🚫 본문 내 이미지 금지 (Purity of Content)
- LLM은 더 이상 본문 HTML(`content`) 안에 `<img>` 태그를 직접 삽입하지 않습니다.
- 모든 이미지는 `image_url` 필드를 통해 독립적으로 관리되어, UI 프리뷰에서 더욱 깔끔하게 렌더링됩니다.

---

## 🎨 4. 프리뷰 및 결과 확인

Swagger 응답만으로는 디자인을 확인하기 어렵습니다. 전용 프리뷰 도구를 사용하세요.

```bash
# 1. Mine-AI 폴더로 이동
cd c:/Dev/workspace/project/Mine/Mine-AI

# 2. 프리뷰 실행 (ID와 토큰 입력)
python tools/magazine_preview.py --id [매거진ID] --token "Bearer_토큰값"
```

> [!TIP]
> **Figma 디자인 반영**: 생성된 `preview_magazine_*.html` 파일은 `매거진/Page` 폴더의 피그마 디자인을 미러링하여 Glassmorphism과 정교한 타이포그래피가 적용된 상태로 보여집니다.

---

## ☁️ 5. GPU 연동 (고화질 이미지 생성 시)

로컬 노트북 성능이 부족할 경우 Google Colab을 통해 GPU 가속을 받을 수 있습니다.

1. `Mine-AI/tools/colab_server.py` 코드 복사.
2. Colab(GPU T4 선택)에서 실행.
3. 생성된 `ngrok` URL을 `.env`의 `REMOTE_IMAGE_SERVER_URL`에 저장.
4. Python 서버 재시작.

---

### ✅ 오늘의 체크리스트
- [ ] `git pull`을 통해 최신 CIJ3 브랜치를 가져왔는가?
- [ ] Redis Docker 컨테이너가 실행 중인가?
- [ ] `image_url`이 본문과 분리되어 섹션 데이터에 포함되었는가?
- [ ] 프리뷰 화면에서 `split_left/right`가 교차되어 나타나는가?
