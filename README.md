# M:ine AI - AI 기반 초 개인화 매거진 플랫폼


> **모든 관심사를 한눈에 나만의 매거진으로 🎨**

M:ine AI는 사용자가 원하는 어떤 주제든 실시간으로 웹 검색하고, AI가 편집하여 고품질 매거진 콘텐츠를 생성하는 FastAPI 기반 백엔드 서버입니다. 패션, 여행, 음악, 건강 등 모든 분야의 매거진을 자동으로 생성하며, 사용자 맞춤형 무드보드 이미지까지 제공합니다.

---

## ✨ 주요 기능

### 🎨 **1. AI 매거진 자동 생성**
- **모든 주제 지원**: 패션, 여행, 음악, 건강, 라이프스타일 등 제한 없음
- **실시간 웹 검색**: Tavily API를 통한 최신 정보 수집
- **고품질 콘텐츠**: Vogue, GQ, Kinfolk 스타일의 세련된 한국어 매거진
- **구조화된 출력**: 제목, 도입부, 섹션별 본문, 태그, 고해상도 이미지 포함
- **사용자 맞춤형**: 사용자 관심사를 반영한 톤 & 스타일 자동 조정

### 🖼️ **2. 무드보드 이미지 생성 (Stable Diffusion XL on RunPod)**
- **GPU 가속 이미지 생성**: RunPod Serverless 기반 Stable Diffusion XL (RTX 4090)
- **로컬 개발 지원**: Mac M-series (MPS) 가속도 지원
- **맞춤형 프롬프트**: 사용자 취향, 매거진 태그, 주제를 바탕으로 프롬프트 자동 생성
- **고품질 배경**: 프로필 배경, 앱 인터페이스용 고급 분위기의 추상/텍스처 이미지
- **다양성 보장**: 랜덤 변형 요소로 매번 다른 스타일 제공

### 💬 **3. AI 에이전트 기반 매거진 편집 (Chat-based Editing)**
- **자연어 명령**: "첫 번째 섹션을 더 감성적으로 바꿔줘"
- **의도 분류 시스템**: 사용자 메시지를 분석하여 액션 자동 결정
  - `APPEND_CONTENT`: 기존 내용 보존 + 새 내용 추가
  - `CHANGE_TONE`: 톤/스타일만 변경
  - `FULL_REWRITE`: 전체 재작성
- **매거진 레벨 편집**:
  - 특정 섹션 재생성 (`regenerate_section`)
  - 새 섹션 추가 (`add_section`)
  - 섹션 삭제 (`delete_section`)
  - 전체 톤 변경 (`change_tone`)
- **섹션 레벨 편집**: 개별 섹션 단위 세밀한 수정
- **실시간 검색 기반**: 새 섹션 추가 시 Tavily로 최신 정보 자동 검색

### 🧠 **4. 인텔리전트 웹 검색 및 크롤링**
- **Tavily Search**: 검색 깊이 조절 (advanced), 이미지 자동 수집
- **Jina AI Reader**: URL → 깔끔한 마크다운 본문 추출
- **폴백 처리**: 검색 실패 시 고품질 Unsplash 플레이스홀더 이미지 제공

### 🔌 **5. Spring Boot 백엔드 연동 (Gateway Pattern)**
- Python AI 서버는 콘텐츠 **생성만** 담당
- Spring 서버가 MySQL 저장 및 비즈니스 로직 처리
- RESTful API 설계로 완전한 분리

### 🚀 **6. RunPod Serverless 배포 & CI/CD**
- **GPU 서버리스**: RunPod Serverless로 RTX 4090 GPU 활용
- **자동 배포**: GitHub Actions → Docker Hub → RunPod 자동 배포
- **Discord 알림**: 배포 상태 실시간 알림
- **Cold Start 최적화**: 경량 Docker 이미지로 빠른 시작

---

## 🏗️ 아키텍처

```
┌─────────────────┐         ┌─────────────────────┐      ┌─────────────────┐
│   Spring Boot   │         │   M:ine AI          │      │ External APIs   │
│   (Backend)     │◄───────►│   (RunPod/FastAPI)  │◄────►│                 │
│                 │         │                     │      │ • OpenAI GPT    │
│ • MySQL Storage │         │ • Magazine Gen      │      │ • Tavily Search │
│ • Business      │         │ • Moodboard Gen     │      │ • Jina Reader   │
│   Logic         │         │ • Section Edit      │      └─────────────────┘
│ • User Auth     │         │ • Intent Analysis   │
└────────▲────────┘         └──────────┬──────────┘
         │                             │
         │                  ┌──────────▼──────────┐
    ┌────▼─────┐            │   GPU Inference     │
    │  Client  │            │   (Stable Diff XL)  │
    │(Frontend)│            │   RTX 4090 @ RunPod │
    └──────────┘            └─────────────────────┘

                    ┌─────────────────────────────┐
                    │   CI/CD Pipeline            │
                    │ GitHub → Docker Hub → RunPod│
                    │ + Discord Notifications     │
                    └─────────────────────────────┘
```

---

## 🛠️ 기술 스택

### **Backend Framework**
- **FastAPI**: 고성능 비동기 웹 프레임워크
- **Uvicorn**: ASGI 서버
- **Pydantic**: 데이터 검증 및 설정 관리

### **AI & NLP**
- **OpenAI GPT-3.5-turbo**: 매거진 콘텐츠 생성, 채팅 분석
- **Local Stable Diffusion XL**: 무드보드 이미지 생성
- **Diffusers (Hugging Face)**: Stable Diffusion 파이프라인
- **PyTorch**: 딥러닝 프레임워크 (MPS 가속)

### **Web Scraping & Search**
- **Tavily API**: AI 친화적 검색 엔진 (이미지 포함)
- **Jina AI Reader**: URL → 마크다운 변환
- **Requests**: HTTP 요청
- **BeautifulSoup4**: HTML 파싱

### **Configuration**
- **python-dotenv**: 환경 변수 관리
- **pydantic-settings**: 타입 안전 설정 관리

---

## 📂 프로젝트 구조

```
Mine-AI/
├── app/
│   ├── main.py                    # FastAPI 앱 진입점, 라우터 등록
│   ├── config.py                  # 환경 변수 설정 (Pydantic)
│   │
│   ├── api/                       # API 엔드포인트 (라우터)
│   │   ├── agent.py               # AI 에이전트 채팅
│   │   ├── analysis.py            # 텍스트 요약
│   │   ├── crawling.py            # 웹 크롤링
│   │   ├── magazine.py            # 매거진 생성 API
│   │   └── chat.py                # 매거진 편집 채팅 API
│   │
│   ├── core/                      # 핵심 비즈니스 로직
│   │   ├── llm_client.py          # OpenAI LLM 클라이언트 (텍스트/JSON 생성)
│   │   ├── llm_gateway.py         # LLM 게이트웨이 (요약, 태깅, 채팅)
│   │   ├── local_diffusion_client.py  # Stable Diffusion XL (MPS/CUDA)
│   │   ├── searcher.py            # Tavily 검색 + Jina 크롤링
│   │   ├── magazine_maker.py      # 매거진 콘텐츠 생성 오케스트레이터
│   │   ├── magazine_editor.py     # 매거진/섹션 편집 + 의도 분류
│   │   ├── moodboard_maker.py     # 무드보드 이미지 생성 오케스트레이터
│   │   └── crawler.py             # 웹 크롤러
│   │
│   └── models/                    # Pydantic 데이터 모델
│       ├── agent.py               # 에이전트 채팅 모델
│       ├── analysis.py            # 분석 요청/응답 모델
│       ├── chat.py                # 매거진 채팅 편집 모델
│       └── magazine.py            # 매거진 데이터 모델
│
├── handler.py                     # RunPod Serverless 핸들러
├── Dockerfile.serverless          # RunPod용 Docker 이미지
│
├── .github/
│   └── workflows/
│       ├── deploy-runpod.yml      # RunPod 자동 배포
│       ├── ci.yml                 # CI 테스트
│       └── discord-notify.yml     # Discord 알림
│
├── tests/                         # 테스트 코드
│   ├── test_moodboard_api.py      # 무드보드 API 테스트
│   └── test_moodboard_variety.py  # 무드보드 다양성 테스트
│
├── .env                           # 환경 변수 (Git 제외)
├── .gitignore
├── requirements.txt               # Python 의존성
└── README.md
```

---

## 🚀 설치 및 실행

### **1. 사전 요구사항**
- Python 3.9 이상
- OpenAI API Key
- Tavily API Key
- (선택) Mac M-series (MPS) 또는 CUDA GPU (로컬 Stable Diffusion용)
- (선택) RunPod API Key (Serverless 배포용)

### **2. 저장소 클론 및 가상환경 설정**
```bash
# 저장소 클론
git clone <repository-url>
cd Mine-AI

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Mac/Linux
# .\\venv\\Scripts\\activate   # Windows
```

### **3. 의존성 설치**
```bash
pip install -r requirements.txt
```

**주요 의존성**:
- `fastapi`, `uvicorn[standard]`: 웹 프레임워크
- `openai`: GPT API
- `tavily-python`: 검색 API
- `diffusers`, `transformers`, `torch`: Stable Diffusion
- `beautifulsoup4`, `requests`: 크롤링

### **4. 환경 변수 설정**
`.env` 파일을 프로젝트 루트에 생성:

```env
# OpenAI API Key (필수)
OPENAI_API_KEY=sk-...

# Tavily Search API Key (필수)
TAVILY_API_KEY=tvly-...

# Jina AI Reader API Key (선택, 없어도 작동)
JINA_API_KEY=jina_...

# Spring Boot 서버 URL (Gateway 연동용)
SPRING_API_URL=http://localhost:8080
```

### **5. 서버 실행 (로컬)**
```bash
uvicorn app.main:app --reload
```

서버가 `http://localhost:8000`에서 실행됩니다.

### **6. RunPod Serverless 배포**
```bash
# Docker 이미지 빌드
docker build -f Dockerfile.serverless -t mine-ai-serverless .

# Docker Hub에 푸시
docker tag mine-ai-serverless jiminjang/mine-ai-serverless:latest
docker push jiminjang/mine-ai-serverless:latest

# GitHub main 브랜치 푸시 시 자동 배포됨
git push origin main
```

---

## 📖 API 사용법

### **API 문서 확인**
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### **주요 엔드포인트**

#### **1️⃣ 매거진 생성**
```http
POST /api/magazine/create
Content-Type: application/json

{
  "topic": "제주도 겨울 여행",
  "user_email": "user@example.com",
  "user_mood": "따뜻하고 감성적인",
  "user_interests": ["여행", "사진", "카페"]
}
```

**응답**:
```json
{
  "title": "제주 겨울, 꼭 가야 할 5곳",
  "introduction": "겨울 제주는 여름과는 다른 매력이 있다...",
  "cover_image_url": "https://...",
  "sections": [
    {
      "heading": "성산일출봉의 겨울 일출",
      "content": "새해 첫날, 성산일출봉에서 맞이하는 일출은...",
      "image_url": "https://...",
      "layout_hint": "image_left"
    }
  ],
  "tags": ["제주여행", "겨울추천", "감성여행"]
}
```

#### **2️⃣ 무드보드 생성**
```http
POST /api/magazine/moodboard
Content-Type: application/json

{
  "topic": "미니멀 라이프",
  "user_mood": "차분하고 세련된",
  "user_interests": ["인테리어", "미니멀리즘"],
  "magazine_tags": ["미니멀", "심플", "모던"],
  "magazine_titles": ["나만의 공간 만들기"]
}
```

**응답**:
```json
{
  "image_url": "data:image/png;base64,iVBORw0KGgoAAAANS...",
  "description": "abstract geometric shapes, soft pastel colors, minimalist, high quality, 8k, cinematic lighting, wallpaper, texture"
}
```

#### **3️⃣ 매거진 편집 (AI 채팅)**
```http
POST /api/magazine/chat
Content-Type: application/json

{
  "magazine_id": 123,
  "magazine_data": { /* 전체 매거진 데이터 */ },
  "user_message": "첫 번째 섹션을 더 감성적으로 바꿔줘"
}
```

**응답**:
```json
{
  "intent": "regenerate_section",
  "success": true,
  "updated_magazine": {
    "heading": "첫 번째 섹션을 더 감성적으로 수정했습니다.",
    "new_sections": [...],
    "deleted_section_ids": []
  }
}
```

#### **4️⃣ 섹션 편집 (Section-Level)**
```http
POST /api/edit_section
Content-Type: application/json

{
  "section_data": {
    "id": 101,
    "heading": "성산일출봉의 겨울 일출",
    "content": "<p>새해 첫날, 성산일출봉에서 맞이하는 일출은...</p>"
  },
  "message": "여기에 카페 추천도 추가해줘"
}
```

**응답**:
```json
{
  "intent": "APPEND_CONTENT",
  "success": true,
  "updated_section": {
    "heading": "성산일출봉의 겨울 일출",
    "content": "<p>새해 첫날, 성산일출봉에서 맞이하는 일출은...</p><p>근처 카페 추천: ...</p>"
  }
}
```

#### **5️⃣ AI 에이전트 채팅**
```http
POST /api/agent/chat
Content-Type: application/json

{
  "user_id": "user123",
  "message": "최신 겨울 코트 트렌드 알려줘"
}
```

---

## 🧪 테스트

### **무드보드 다양성 테스트**
```bash
python tests/test_moodboard_variety.py
```
같은 주제로 5번 생성하여 이미지 다양성 확인

### **무드보드 API 테스트**
```bash
python tests/test_moodboard_api.py
```

---

## 🎯 핵심 설계 철학

### **1. Gateway Pattern (Python ↔ Spring 분리)**
- **Python**: AI 콘텐츠 생성만 담당 (Stateless)
- **Spring**: 데이터 저장, 인증, 비즈니스 로직 담당
- **장점**: 각 서버의 책임 명확, 독립적 확장 가능

### **2. Informative & Sophisticated 매거진**
- **정보 우선**: 구체적인 사실, 숫자, 이름, 위치 포함
- **세련된 문체**: Vogue, GQ, Kinfolk 스타일의 고급스러운 톤
- **명확성 유지**: 시적 표현보다 명확한 정보 전달 우선

### **3. GPU Serverless (확장성 + 비용 최적화)**
- RunPod Serverless로 RTX 4090 GPU 온디맨드 사용
- 로컬 개발: Mac MPS / CUDA 가속 지원
- Lazy Loading으로 Cold Start 시간 단축
- 사용량 기반 과금으로 비용 최적화

### **4. Multi-Source Search (정확도 향상)**
- **Tavily**: 빠른 검색 + 이미지 수집
- **Jina AI**: 깊이 있는 본문 읽기 (Top 1 URL)
- **Fallback**: 검색 실패 시 고품질 플레이스홀더 제공

### **5. Extensible LLM Client**
- OpenAI API를 추상화한 `LLMClient` 클래스
- 향후 로컬 LoRA 모델, Claude, Gemini 등 쉽게 교체 가능
- `generate_text()`, `generate_json()` 메서드 제공

---

## 🔧 고급 기능 및 최적화

### **Stable Diffusion 최적화**
```python
# app/core/local_diffusion_client.py

# MPS (Mac M-series) 가속
self.pipe.to("mps")

# 메모리 최적화 (옵션)
# self.pipe.enable_attention_slicing()

# FP16 사용으로 속도 향상
torch_dtype=torch.float16
```

### **이미지 URL 검증 및 보정**
```python
# app/core/magazine_maker.py

# AI가 잘못된 URL을 생성할 경우 자동 보정
if not result_json.get('cover_image_url').startswith('http'):
    result_json['cover_image_url'] = images[0]
```

### **한국어 서수 자동 변환**
```python
# app/core/magazine_editor.py

# "첫 번째" → index 0
# "두 번째" → index 1
# AI가 자동 변환하여 정확한 섹션 편집
```

---

## 🌟 사용 시나리오

### **시나리오 1: 패션 매거진 생성**
1. 사용자가 "2024 겨울 코트 트렌드" 검색
2. Tavily가 최신 패션 기사 검색 + 고화질 이미지 수집
3. Jina AI가 상위 1개 기사 본문 깊이 읽기
4. GPT-3.5가 Vogue 스타일 매거진 작성
5. Stable Diffusion XL이 무드보드 배경 이미지 생성

### **시나리오 2: AI 채팅으로 매거진 커스터마이징**
1. 사용자: "첫 번째 섹션을 더 감성적으로 바꿔줘"
2. AI가 의도 분석 → `regenerate_section` 액션 결정
3. 원본 이미지는 유지하면서 텍스트만 재생성
4. 사용자: "009의 앨범 추천 섹션 추가해줘"
5. AI가 Tavily로 009 앨범 정보 검색 → 새 섹션 생성

### **시나리오 3: 무드보드 재생성 (Re-roll)**
1. 사용자가 무드보드 생성
2. 마음에 안 들면 같은 파라미터로 재요청
3. `random.choice(variations)`로 매번 다른 스타일 프롬프트 생성
4. 완전히 다른 이미지 획득 (무제한 재생성)

---

## 🚧 향후 개발 계획

- [x] ~~RunPod Serverless 배포~~ ✅
- [x] ~~CI/CD 파이프라인~~ ✅
- [x] ~~섹션 레벨 편집~~ ✅
- [x] ~~의도 분류 시스템~~ ✅
- [ ] **이미지 S3 저장**: Data URI 대신 S3 업로드 후 URL 반환
- [ ] **LoRA Fine-tuning**: M:ine 스타일 전용 경량 모델 학습
- [ ] **다국어 지원**: 영어, 일본어 매거진 생성
- [ ] **음성 기반 편집**: "Hey M:ine, 첫 번째 섹션 바꿔줘"
- [ ] **자동 레이아웃 추천**: 섹션 개수/이미지 비율에 따른 최적 레이아웃
- [ ] **실시간 협업**: 여러 사용자가 동시에 매거진 편집

---

## 📝 라이센스

MIT License

---

## 🙏 coop

- **OpenAI**: GPT-3.5-turbo API
- **Stability AI**: Stable Diffusion XL 모델
- **Tavily**: AI 친화적 검색 엔진
- **Jina AI**: 깔끔한 웹 크롤링 서비스
- **Hugging Face**: Diffusers 라이브러리

---

<div align="center">

team:SOULution
Mine
## 👥 Contributors

<table align="center">
  <tr>
    <td align="center" width="150px">
      <a href="https://github.com/jangjimin9766">
        <img src="https://github.com/jangjimin9766.png" width="100px" style="border-radius:50%"/>
      </a>
    </td>
  </tr>
  <tr>
    <td align="center">
      <b>장지민</b><br/>
      <a href="https://github.com/jangjimin9766">@jangjimin9766</a><br/>
     <b> Tech Lead</b><br/>
      AI Engineering<br/>
      Prompt Engineering<br/>
      Model Optimization (MPS)
    </td>
  </tr>
</table>

</div>
