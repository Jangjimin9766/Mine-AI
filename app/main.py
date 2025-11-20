from fastapi import FastAPI
from app.api import agent, analysis, crawling, magazine # magazine 추가

app = FastAPI(
    title="M:ine AI Server",
    description="AI Agent, Analysis, and Crawling server for the M:ine project.",
    version="0.1.0"
)

app.include_router(agent.router, prefix="/api/agent", tags=["AI Agent"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["AI Analysis"])
app.include_router(crawling.router, prefix="/api/crawling", tags=["Crawling"])
# 새로 추가된 라우터
app.include_router(magazine.router, prefix="/api/magazine", tags=["Magazine Factory"])

@app.get("/")
def read_root():
    return {"message": "Welcome to M:ine AI Server"}