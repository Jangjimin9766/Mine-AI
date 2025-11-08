from fastapi import FastAPI
from app.api import agent, analysis, crawling

app = FastAPI(
    title="M:ine AI Server",
    description="AI Agent, Analysis, and Crawling server for the M:ine project.",
    version="0.1.0"
)

# --- API 라우터 포함 ---
app.include_router(agent.router, prefix="/api/agent", tags=["AI Agent"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["AI Analysis"])
app.include_router(crawling.router, prefix="/api/crawling", tags=["Crawling"])


@app.get("/")
def read_root():
    """
    서버 상태 확인을 위한 루트 엔드포인트
    """
    return {"message": "Welcome to M:ine AI Server"}