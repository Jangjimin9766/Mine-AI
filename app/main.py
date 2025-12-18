from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.api import agent, analysis, crawling, magazine, chat
from app.config import settings

app = FastAPI(title="M:ine AI Server")

# --- Security Configuration ---
async def verify_api_key(x_api_key: str = Header(...)):
    """Validates the API Key sent in the header"""
    if x_api_key != settings.PYTHON_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록 (API Key 보안 적용)
api_dependencies = [Depends(verify_api_key)]

app.include_router(agent.router, prefix="/api/agent", tags=["agent"], dependencies=api_dependencies)
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"], dependencies=api_dependencies)
app.include_router(crawling.router, prefix="/api/crawling", tags=["crawling"], dependencies=api_dependencies)
app.include_router(magazine.router, prefix="/api/magazine", tags=["magazine"], dependencies=api_dependencies)
app.include_router(chat.router, prefix="/api/magazine", tags=["chat"], dependencies=api_dependencies)  # 채팅 라우터 추가

@app.get("/")
def read_root():
    return {"message": "M:ine AI Server is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}