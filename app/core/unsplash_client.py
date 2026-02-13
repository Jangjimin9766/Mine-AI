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
    - 영어 키워드(V4): 콤마로 구분된 경우 첫 번째가 핵심 피사체이므로 유지.
    - 한글 키워드: 장소, 피사체 순서인 경우 뒤쪽 피사체를 강조.
    """
    if not query:
        return ""

    # 콤마가 있으면 분석
    if "," in query:
        parts = [p.strip() for p in query.split(",")]
        
        # 영어 키워드인 경우 (알파벳 비율이 높은 경우)
        is_english = sum(1 for c in query if c.isalpha()) / len(query.strip() or " ") > 0.5
        
        if is_english:
            # 첫 번째 파트(피사체) + 마지막 파트(무드) 조합
            if len(parts) >= 2:
                subject = parts[0]
                style = parts[-1]
                # 너무 똑같으면 하나만
                if subject.lower() in style.lower() or style.lower() in subject.lower():
                    return subject
                return f"{subject} {style}"
            return parts[0]
            
        # 한글 키워드인 경우 (기존 로직 유지하되 보완)
        back = parts[-1]
        front_keywords = parts[0].replace("의", " ").replace("에서", " ").strip()
        
        if len(front_keywords) > 10:
            return back
        return f"{back} {front_keywords}"
    
    return query


def get_default_fallback() -> str:
    """기본 fallback 이미지 반환"""
    return "https://images.unsplash.com/photo-1557683316-973673baf926?w=1200"
