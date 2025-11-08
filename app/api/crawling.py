from fastapi import APIRouter, BackgroundTasks
# [수정] 클래스가 아닌 함수를 임포트
from app.core.crawler import crawl_fashion_site 
# from app.config import settings # (DB 저장 시 필요)
# import requests # (DB 저장 시 필요)

router = APIRouter()

def run_crawling_task(url: str):
    """
    백그라운드에서 실행될 실제 크롤링 작업
    """
    # [수정] 임포트한 함수를 바로 호출
    result = crawl_fashion_site(url)
    
    # (TODO: 크롤링 결과를 Spring Boot 서버로 POST)
    # print(f"Crawling task finished for {url}. Result: {result.get('title')}")
    # requests.post(f"{settings.SPRING_API_URL}/api/internal/crawled-data", json=result)


@router.post("/start-crawl")
def api_start_crawl(url: str, background_tasks: BackgroundTasks):
    """
    크롤링 작업을 백그라운드로 실행하도록 요청합니다.
    """
    background_tasks.add_task(run_crawling_task, url)
    
    return {"message": "Crawling task started in background", "url": url}