from fastapi import APIRouter
from app.models.agent import ChatRequest, ChatResponse
from app.core.llm_gateway import get_agent_response
# 두 함수 모두 임포트
from app.core.searcher import search_with_tavily, scrape_with_jina 

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def handle_chat_request(request: ChatRequest):
    
    # 1. [Tavily] 검색해서 후보군 찾기
    search_results, images = search_with_tavily(request.message)
    
    full_content = ""
    
    # 2. [Jina AI] 상위 1개 링크만 들어가서 '깊게 읽기' (Deep Dive)
    if search_results:
        top_url = search_results[0]['url'] # 가장 정확도가 높은 첫 번째 링크
        print(f"🤖 Agent selected best URL: {top_url}")
        
        # Jina가 깔끔하게 긁어온 본문
        full_content = scrape_with_jina(top_url) 
        
        # 만약 Jina가 실패하면 Tavily의 짧은 요약본이라도 씀
        if not full_content:
            full_content = search_results[0]['content']

    # 3. 데이터 패키징
    collected_data = {
        "source_url": search_results[0]['url'] if search_results else "",
        "deep_content": full_content[:2000], # 본문이 너무 길면 GPT 토큰 아끼기 위해 자름
        "found_images": images[:3]
    }
    
    # 4. [AI] 최종 답변 생성 (훨씬 풍부한 내용을 바탕으로!)
    ai_answer = get_agent_response(request, collected_data)
    
    return ChatResponse(answer=ai_answer)