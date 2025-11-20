from tavily import TavilyClient
import requests
from app.config import settings

# Tavily 클라이언트 초기화 (settings에서 키 로드)
# .env 파일에 TAVILY_API_KEY가 반드시 있어야 합니다.
tavily = TavilyClient(api_key=settings.TAVILY_API_KEY)

def search_with_tavily(query: str):
    """
    Tavily를 이용해 검색하고, AI가 읽기 좋은 답변과 이미지를 가져옵니다.
    """
    print(f"🔎 Tavily Searching for: {query}")
    
    try:
        # search_depth="advanced": 좀 더 깊이 있게 검색
        # include_images=True: 이미지도 같이 찾아줌 (M:ine에 필수!)
        response = tavily.search(
            query=query,
            search_depth="advanced",
            include_images=True,
            max_results=3
        )
        
        # Tavily는 이미 요약된 content를 줍니다.
        return response.get('results', []), response.get('images', [])

    except Exception as e:
        print(f"❌ Tavily Error: {e}")
        return [], []

def scrape_with_jina(url: str):
    """
    Jina AI Reader를 사용하여 URL의 본문을 마크다운으로 깔끔하게 가져옵니다.
    """
    print(f"📖 Jina Reading: {url}")
    
    # Jina는 URL 앞에 'https://r.jina.ai/'만 붙이면 됩니다.
    jina_url = f"https://r.jina.ai/{url}"
    
    headers = {
        "Authorization": f"Bearer {settings.JINA_API_KEY}" # 키가 없어도 되긴 하는데, 있으면 안정적
    }
    
    try:
        response = requests.get(jina_url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.text # 깔끔한 마크다운 텍스트 반환
        else:
            print(f"⚠️ Jina request failed with status: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Jina Error: {e}")
        return None