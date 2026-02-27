"""
Unsplash API 클라이언트
문단별로 정확한 이미지를 검색하기 위한 모듈
"""
import requests
from app.config import settings

UNSPLASH_API_URL = "https://api.unsplash.com/search/photos"

# 캐시: 동일 검색어 반복 시 다른 이미지를 주기 위해 리스트 저장
_image_cache = {}
_cache_index = {}

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
    
    # 캐시 확인 (인덱스 순회하며 새로운 이미지 반환)
    if query in _image_cache:
        urls = _image_cache[query]
        idx = _cache_index.get(query, 0)
        
        if idx < len(urls):
            image_url = urls[idx]
            _cache_index[query] = idx + 1
            print(f"📦 Unsplash cache hit: {query} (idx {idx}/{len(urls)})")
            return image_url
        else:
            # 10장을 다 썼다면 다시 처음으로
            _cache_index[query] = 1
            print(f"📦 Unsplash cache cycle reset: {query}")
            return urls[0]
    
    # 검색어 정제 (콤마 이후 부분만 사용하거나 전체 사용)
    clean_query = _clean_query(query)
    
    try:
        response = requests.get(
            UNSPLASH_API_URL,
            params={
                "query": clean_query,
                "per_page": 10,  # 10장 미리 가져와서 캐싱
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
                # 정규 사이즈 이미지 URL (1080px) 리스트 수집
                urls = [r.get("urls", {}).get("regular") for r in results if r.get("urls", {}).get("regular")]
                
                if urls:
                    print(f"✅ Unsplash found {len(urls)} images: {clean_query}")
                    _image_cache[query] = urls
                    _cache_index[query] = 1
                    return urls[0]
        
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
    """기본 fallback 이미지 반환 — 빈 문자열 대신 None을 반환하여 후속 fallback 로직이 작동하도록 함"""
    return None
