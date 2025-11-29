from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import agent, analysis, crawling, magazine, chat

app = FastAPI(title="M:ine AI Server")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(crawling.router, prefix="/api/crawling", tags=["crawling"])
app.include_router(magazine.router, prefix="/api/magazine", tags=["magazine"])
app.include_router(chat.router, prefix="/api/magazine", tags=["chat"])  # 채팅 라우터 추가

@app.get("/")
def read_root():
    return {"message": "M:ine AI Server is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}