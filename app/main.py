from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import agent, analysis, crawling, magazine # magazine 추가

app = FastAPI(
    title="M:ine AI Server",
    description="AI Agent, Analysis, and Crawling server for the M:ine project.",
    version="0.1.0"
)

# [CORS 설정] 로컬에서 HTML 파일로 바로 API 호출할 수 있게 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 실제 배포 시에는 구체적인 도메인으로 제한해야 함
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent.router, prefix="/api/agent", tags=["AI Agent"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["AI Analysis"])
app.include_router(crawling.router, prefix="/api/crawling", tags=["Crawling"])
# 새로 추가된 라우터
app.include_router(magazine.router, prefix="/api/magazine", tags=["Magazine Factory"])

@app.get("/")
def read_root():
    return {"message": "Welcome to M:ine AI Server"}