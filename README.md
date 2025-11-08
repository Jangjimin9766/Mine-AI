# Mine-AI

AI 기반 데이터 분석 및 채팅 서비스

## 기능

- AI 에이전트와의 채팅
- 데이터 분석
- 웹 크롤링
- Spring 서버와의 연동

## 설치

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# 의존성 설치
pip install -r requirements.txt
```

## 환경 변수 설정

`.env` 파일을 생성하고 다음 변수들을 설정하세요:

```
OPENAI_API_KEY=your_openai_api_key
SPRING_SERVER_URL=http://localhost:8080
```

## 실행

```bash
uvicorn app.main:app --reload
```

## API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
