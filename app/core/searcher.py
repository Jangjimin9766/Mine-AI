from tavily import TavilyClient
import requests
from app.config import settings

# Tavily 클라이언트는 함수 내에서 지연 초기화 (CI 테스트 호환성)
_tavily_client = None

def _get_tavily_client():
    """Tavily 클라이언트를 지연 초기화하여 반환"""
    global _tavily_client
    if _tavily_client is None:
        api_key = settings.TAVILY_API_KEY
        if not api_key or api_key == "test-key":
            return None  # 테스트 환경에서는 None 반환
        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client

def search_with_tavily(query: str):
    """
    Tavily를 이용해 검색하고, AI가 읽기 좋은 답변과 이미지를 가져옵니다.
    이미지가 없으면 플레이스홀더 이미지를 사용합니다.
    """
    print(f"🔎 Tavily Searching for: {query}")
    
    # 플레이스홀더 이미지 (Tavily 실패 시 사용)
    FALLBACK_IMAGES = [
        "https://images.unsplash.com/photo-1557683316-973673baf926?w=1200",  # Gradient
        "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=1200",  # Abstract
        "https://images.unsplash.com/photo-1557682250-33bd709cbe85?w=1200",  # Gradient 2
        "https://images.unsplash.com/photo-1558591710-4b4a1ae0f04d?w=1200",  # Abstract 2
        "https://images.unsplash.com/photo-1557682224-5b8590cd9ec5?w=1200",  # Gradient 3
    ]
    
    # Tavily 클라이언트 가져오기 (없으면 fallback)
    tavily = _get_tavily_client()
    if tavily is None:
        print(f"⚠️ Tavily API key not configured, using fallback")
        return [], FALLBACK_IMAGES
    
    try:
        # search_depth="advanced": 좀 더 깊이 있게 검색
        # include_images=True: 이미지도 같이 찾아줌 (M:ine에 필수!)
        response = tavily.search(
            query=query,
            search_depth="advanced",
            include_images=True,
            max_results=3
        )
        
        results = response.get('results', [])
        images = response.get('images', [])
        
        # 이미지가 없으면 플레이스홀더 사용
        if not images or len(images) == 0:
            print(f"⚠️ No images found, using fallback images")
            images = FALLBACK_IMAGES
        
        # 최소 5개 이미지 보장
        while len(images) < 5:
            images.extend(FALLBACK_IMAGES)
        
        print(f"✅ Found {len(results)} results and {len(images)} images")
        return results, images[:10]  # 최대 10개까지만

    except Exception as e:
        print(f"❌ Tavily Error: {e}, using fallback")
        return [], FALLBACK_IMAGES

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