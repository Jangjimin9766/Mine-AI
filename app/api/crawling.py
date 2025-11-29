from fastapi import APIRouter, BackgroundTasks
from app.core.crawler import crawl_fashion_site
# [추가] AI 함수들 임포트
from app.core.llm_gateway import get_llm_summary, get_tags_from_text 

router = APIRouter()

def run_crawling_task(url: str):
    """
    [크롤링 -> AI 요약 -> AI 태깅] 파이프라인 실행
    """
    print(f"🚀 Task Started: Processing {url}")
    
    # 1. 크롤링 (데이터 수집)
    data = crawl_fashion_site(url)
    
    if data.get("status") == "fail":
        print("⚠️ Crawling failed, stopping task.")
        return

    # 2. AI 요약 (데이터 가공)
    summary = get_llm_summary(data["content"])
    data["summary"] = summary # 결과에 추가

    # 3. AI 태깅 (데이터 분석)
    tags = get_tags_from_text(data["content"])
    data["tags"] = tags # 결과에 추가

    # 4. 결과 확인 (나중에는 여기서 Spring 서버로 전송함)
    print("\n" + "="*40)
    print(f"✅ [COMPLETE] {data['title']}")
    print(f"📝 Summary: {data['summary']}")
    print(f"🏷️ Tags: {data['tags']}")
    print("="*40 + "\n")
    
    # TODO: requests.post(SPRING_API_URL, json=data)


@router.post("/start-crawl")
def api_start_crawl(url: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_crawling_task, url)
    return {"message": "Crawling & Analysis started", "url": url}