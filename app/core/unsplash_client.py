"""
Unsplash API 클라이언트
문단별로 정확한 이미지를 검색하기 위한 모듈
"""
import requests
from app.config import settings

UNSPLASH_API_URL = "https://api.unsplash.com/search/photos"

# 캐시: 동일 검색어 반복 방지
_image_cache = {}


def search_unsplash_image(query: str, fallback_url: str = None) -> str:
    """
    Unsplash에서 검색어에 맞는 이미지를 가져옵니다.
    
    Args:
        query: 검색어 (예: "국밥의 성지, 서면" → "서면 돼지국밥")
        fallback_url: 검색 실패 시 사용할 대체 URL
        
    Returns:
        이미지 URL (실패 시 fallback_url 반환)
    """
    # API 키 확인
    access_key = settings.UNSPLASH_ACCESS_KEY
    if not access_key:
        print(f"⚠️ Unsplash API key not configured, using fallback")
        return fallback_url or get_default_fallback()
    
    # 캐시 확인
    if query in _image_cache:
        print(f"📦 Unsplash cache hit: {query}")
        return _image_cache[query]
    
    # 검색어 정제 (콤마 이후 부분만 사용하거나 전체 사용)
    clean_query = _clean_query(query)
    
    try:
        response = requests.get(
            UNSPLASH_API_URL,
            params={
                "query": clean_query,
                "per_page": 1,
                "orientation": "landscape",  # 가로 이미지 선호
                "content_filter": "high"      # 안전한 콘텐츠만
            },
            headers={
                "Authorization": f"Client-ID {access_key}"
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            
            if results and len(results) > 0:
                # 정규 사이즈 이미지 URL (1080px)
                image_url = results[0].get("urls", {}).get("regular")
                if image_url:
                    print(f"✅ Unsplash found: {clean_query} → {image_url[:50]}...")
                    _image_cache[query] = image_url
                    return image_url
        
        print(f"⚠️ Unsplash no results for: {clean_query}")
        return fallback_url or get_default_fallback()
        
    except Exception as e:
        print(f"❌ Unsplash error: {e}")
        return fallback_url or get_default_fallback()


def search_unsplash_images(queries: list, fallback_urls: list = None) -> list:
    """
    여러 검색어에 대해 배치로 이미지를 검색합니다.
    
    Args:
        queries: 검색어 리스트
        fallback_urls: 대체 URL 리스트 (queries와 동일 길이)
        
    Returns:
        이미지 URL 리스트
    """
    results = []
    fallback_urls = fallback_urls or []
    
    for i, query in enumerate(queries):
        fallback = fallback_urls[i] if i < len(fallback_urls) else None
        image_url = search_unsplash_image(query, fallback)
        results.append(image_url)
    
    return results


def _clean_query(query: str) -> str:
    """
    검색어를 정제합니다.
    예: "국밥의 성지, 서면" → "서면 국밥"
    """
    # 콤마가 있으면 뒷부분 우선 사용
    if "," in query:
        parts = query.split(",")
        # 뒷부분 + 앞부분의 핵심 키워드
        back = parts[-1].strip()
        front_keywords = parts[0].replace("의", " ").replace("에서", " ").strip()
        # 너무 길면 뒷부분만
        if len(front_keywords) > 10:
            return back
        return f"{back} {front_keywords}"
    
    return query


def get_default_fallback() -> str:
    """기본 fallback 이미지 반환"""
    return "https://images.unsplash.com/photo-1557683316-973673baf926?w=1200"
