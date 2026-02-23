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

def search_with_tavily(query: str, topic: str = None):
    """
    Tavily를 이용해 검색하고, AI가 읽기 좋은 답변과 이미지를 가져옵니다.
    이미지가 없으면 플레이스홀더 이미지를 사용합니다.
    """
    print(f"🔎 Tavily Searching for: {query} (Topic: {topic})")
    
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
    
    # 검색어 정교화: 주제와 무관한 게임/이미지 노이즈 방지 (도메인 앵커링)
    clean_query = query
    if topic:
        # 중의적 키워드가 있을 경우 주제를 결합하여 도메인 고정
        ambiguous_keywords = ['잠재력', '레벨', '각성', '강화', '아이템', '스킬', '공략', '티어']
        if any(k in query for k in ambiguous_keywords):
            clean_query = f"{topic} {query}"
            print(f"⚓ Domain Anchoring applied: {clean_query}")
    
    try:
        # search_depth="advanced": 좀 더 깊이 있게 검색
        # include_images=True: 이미지도 같이 찾아줌 (M:ine에 필수!)
        response = tavily.search(
            query=clean_query,
            search_depth="advanced",
            include_images=True,
            max_results=5
        )
        
        results = response.get('results', [])
        images = response.get('images', [])
        
        # 이미지 필터링 로직: 게임 위키나 불필요한 도메인 제외 시도 (할루시네이션 방지)
        filtered_images = []
        noise_domains = [
            'wikia', 'fandom', 'game', 'screenshot', 'awakening', 
            'inven', 'ruliweb', 'dcinside', 'namu.wiki', 'strategywiki',
            'mobiware', 'appstore', 'play.google'
        ]
        
        for img in images:
            img_lower = img.lower()
            if any(noise in img_lower for noise in noise_domains):
                continue
            filtered_images.append(img)
        
        images = filtered_images
        
        # 이미지가 없으면 플레이스홀더 사용
        if not images or len(images) == 0:
            print(f"⚠️ No images found after filtering, using fallback images")
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
    실패해도 None을 반환하여 매거진 생성이 계속 진행됩니다.
    """
    print(f"📖 Jina Reading: {url}")
    
    # Jina는 URL 앞에 'https://r.jina.ai/'만 붙이면 됩니다.
    jina_url = f"https://r.jina.ai/{url}"
    
    # API 키가 있을 때만 Authorization 헤더 추가 (없으면 무인증으로 시도)
    headers = {}
    if settings.JINA_API_KEY:
        headers["Authorization"] = f"Bearer {settings.JINA_API_KEY}"
    else:
        print("⚠️ JINA_API_KEY not set, trying without auth...")
    
    try:
        response = requests.get(jina_url, headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Jina read successful")
            return response.text  # 깔끔한 마크다운 텍스트 반환
        else:
            print(f"⚠️ Jina request failed with status: {response.status_code}, continuing without deep content")
            return None
    except Exception as e:
        print(f"⚠️ Jina Error: {e}, continuing without deep content")
        return None


import re

def extract_images_from_content(content: str) -> list:
    """
    Jina가 반환한 마크다운/HTML 콘텐츠에서 이미지 URL을 추출합니다.
    크롤링된 소스의 실제 이미지를 우선적으로 사용하기 위함.
    
    Returns:
        유효한 이미지 URL 리스트 (중복 제거, 노이즈 필터링 완료)
    """
    if not content:
        return []
    
    urls = set()
    
    # 1) 마크다운 이미지: ![alt](url)
    md_pattern = r'!\[[^\]]*\]\((https?://[^\s\)]+)\)'
    for match in re.finditer(md_pattern, content):
        urls.add(match.group(1))
    
    # 2) HTML img 태그: <img src="url"> or <img src='url'>
    html_pattern = r'<img[^>]+src=["\']?(https?://[^\s"\'>\)]+)["\']?'
    for match in re.finditer(html_pattern, content, re.IGNORECASE):
        urls.add(match.group(1))
    
    # 노이즈 이미지 필터링
    noise_patterns = [
        # 아이콘, 로고, 추적 픽셀
        'favicon', 'icon', 'logo', 'badge', 'avatar',
        'pixel', 'tracker', 'beacon', '1x1', 'spacer',
        'emoji', 'button', 'arrow', 'spinner', 'loading',
        # 광고 및 추적
        'ad-', '/ads/', 'adserver', 'doubleclick', 'googlesyndication',
        'facebook.com/tr', 'analytics', 'tracking',
        # SNS 공유 버튼 등
        'share', 'social', 'twitter-card', 'og-image',
        # 너무 작은 이미지 (크기 힌트가 URL에 있는 경우)
        'w=1&', 'h=1&', 'width=1', 'height=1',
        '16x16', '32x32', '48x48', '64x64',
    ]
    
    # 유효한 이미지 확장자
    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.avif']
    
    filtered = []
    for url in urls:
        url_lower = url.lower()
        
        # 노이즈 패턴 체크
        if any(noise in url_lower for noise in noise_patterns):
            continue
        
        # SVG 제외 (보통 아이콘)
        if url_lower.endswith('.svg'):
            continue
        
        # 최소한의 이미지 URL 길이 체크 (너무 짧으면 쓸모없음)
        if len(url) < 30:
            continue
        
        filtered.append(url)
    
    print(f"📰 Extracted {len(filtered)} images from crawled content (out of {len(urls)} total)")
    return filtered


def get_topic_fallback_images(topic: str, count: int = 5) -> list:
    """
    주제 기반으로 Unsplash에서 관련 이미지를 검색하여 fallback으로 사용합니다.
    하드코딩된 파란 그라디언트 대신 주제와 관련 있는 이미지를 제공합니다.
    
    Args:
        topic: 매거진 주제
        count: 필요한 이미지 수
    
    Returns:
        이미지 URL 리스트
    """
    from app.core.unsplash_client import search_unsplash_image
    
    # 기본 fallback (Unsplash 검색도 실패할 경우)
    DEFAULT_FALLBACK = "https://images.unsplash.com/photo-1557683316-973673baf926?w=1200"
    
    # 주제에서 핵심 키워드 추출 (간단한 방식)
    # 한글 주제를 영어로 변환하기 어려우니, 그대로 Unsplash에 검색
    search_variations = [
        topic,                           # 원본 주제
        f"{topic} lifestyle",            # 라이프스타일 앵커
        f"{topic} aesthetic",            # 미학적 앵커
    ]
    
    results = []
    for i in range(count):
        query = search_variations[i % len(search_variations)]
        url = search_unsplash_image(query, DEFAULT_FALLBACK)
        if url and url != DEFAULT_FALLBACK:
            results.append(url)
        else:
            results.append(DEFAULT_FALLBACK)
    
    topic_count = sum(1 for u in results if u != DEFAULT_FALLBACK)
    print(f"🎯 Topic fallback: {topic_count}/{count} topic-related images for '{topic}'")
    return results