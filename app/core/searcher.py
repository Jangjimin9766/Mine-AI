from tavily import TavilyClient
import os
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
    FALLBACK_IMAGES = []
    
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
            max_results=15
        )
        
        results = response.get('results', [])
        images = response.get('images', [])
        
        # 이미지 필터링 로직: 게임 위키나 불필요한 도메인 제외 시도 (할루시네이션 방지)
        filtered_images = []
        noise_domains = [
            'wikia', 'fandom', 'game', 'screenshot', 'awakening', 
            'inven', 'ruliweb', 'dcinside', 'namu.wiki', 'strategywiki',
            'mobiware', 'appstore', 'play.google', 'ytimg.com', 'youtube.com', 'youtu.be',
            'daumcdn.net', 'pstatic.net', 'tistory.com', 'blogfiles.naver.net', 'kakaocdn.net', 'fmkorea', 'theqoo'
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
        if images and len(images) < 5:
            # Try to fetch additional broad images once to guarantee unique photos
            try:
                print(f"🔄 Fetching additional broad images for: {topic}")
                broad_response = tavily.search(
                    query=f"{topic} wallpaper | photography",
                    search_depth="basic",
                    include_images=True,
                    max_results=5
                )
                more_images = broad_response.get('images', [])
                for img in more_images:
                    img_lower = img.lower()
                    if not any(noise in img_lower for noise in noise_domains) and img not in images:
                        images.append(img)
                        if len(images) >= 5:
                            break
            except Exception as e:
                print(f"⚠️ Failed secondary Tavily search: {e}")
                
            # If still not enough, then and only then duplicate
            if len(images) < 5:
                images = (images * 5)[:10]
        elif not images:
            images = []


        
        print(f"✅ Found {len(results)} results and {len(images)} images")
        return results, images[:10]  # 최대 10개까지만

    except Exception as e:
        print(f"❌ Tavily Error: {e}, using fallback")
        return [], FALLBACK_IMAGES

def _is_jina_auth_failure(status_code: int) -> bool:
    return status_code in (401, 402, 403)


def _jina_timeout_seconds() -> float:
    return float(os.getenv("JINA_READ_TIMEOUT_SECONDS", "5"))


def scrape_with_jina(url: str, request_state: dict = None):
    """
    Jina AI Reader를 사용하여 URL의 본문을 마크다운으로 깔끔하게 가져옵니다.
    실패해도 None을 반환하여 매거진 생성이 계속 진행됩니다.
    """
    request_state = request_state if request_state is not None else {}
    request_state.setdefault("auth_disabled", False)
    request_state.setdefault("auth_failure_count", 0)
    request_state.setdefault("timeout_count", 0)
    request_state.setdefault("urls_attempted", 0)
    request_state.setdefault("urls_succeeded", 0)
    request_state.setdefault("urls_failed", 0)

    request_state["urls_attempted"] += 1
    print(f"📖 Jina Reading: {url}")
    
    # Jina는 URL 앞에 'https://r.jina.ai/'만 붙이면 됩니다.
    jina_url = f"https://r.jina.ai/{url}"
    
    # API 키가 있을 때만 Authorization 헤더 추가 (없으면 무인증으로 시도)
    timeout_seconds = _jina_timeout_seconds()
    headers = {}
    if settings.JINA_API_KEY and not request_state.get("auth_disabled"):
        headers["Authorization"] = f"Bearer {settings.JINA_API_KEY}"
    elif not settings.JINA_API_KEY:
        print("⚠️ JINA_API_KEY not set, trying without auth...")
    else:
        print("⚠️ Jina auth disabled for this request, trying without auth...")
    
    try:
        response = requests.get(jina_url, headers=headers, timeout=timeout_seconds)
        if _is_jina_auth_failure(response.status_code) and headers:
            request_state["auth_failure_count"] += 1
            request_state["auth_disabled"] = True
            print("⚠️ Jina API key has insufficient balance, retrying without auth...")
            response = requests.get(jina_url, timeout=timeout_seconds)
        if response.status_code == 200:
            print("✅ Jina read successful")
            request_state["urls_succeeded"] += 1
            return response.text  # 깔끔한 마크다운 텍스트 반환
        else:
            print(f"⚠️ Jina request failed with status: {response.status_code}, continuing without deep content")
            request_state["urls_failed"] += 1
            return None
    except requests.exceptions.Timeout as e:
        request_state["timeout_count"] += 1
        request_state["urls_failed"] += 1
        print(f"⚠️ Jina Timeout: {e}, continuing without deep content")
        return None
    except Exception as e:
        request_state["urls_failed"] += 1
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
        # 아이콘, 로고, 추적 픽셀, UI 요소
        'favicon', 'icon', 'logo', 'badge', 'avatar', 'profile', 'thumb', 'menu', 'nav', 'header', 'footer', 'sidebar',
        'pixel', 'tracker', 'beacon', '1x1', 'spacer', 'blank', 'transparent', 'default',
        'emoji', 'button', 'arrow', 'spinner', 'loading', 'spinner',
        # 사이즈 관련 (작은 이미지나 썸네일 방지)
        'w=1&', 'h=1&', 'width=1', 'height=1', 'w=50', 'h=50',
        '16x16', '32x32', '48x48', '64x64', '100x100', '120x120', '150x150',
        'thumbnail', 'small', 'tiny', 'mini',
        # 광고 및 마케팅 네트워크 (매우 중요)
        'ad-', '/ads/', '-ad-', 'adserver', 'doubleclick', 'googlesyndication', 'googleadservices',
        'adsystem', 'adtech', 'adform', 'criteo', 'taboola', 'outbrain', 'mgid',
        'facebook.com/tr', 'analytics', 'tracking', 'banner', 'sponsor', 'promo', 'campaign',
        # SNS 공유, 카드, 위젯
        'share', 'social', 'twitter-card', 'og-image', 'widget', 'plugin',
        # 외부 다운로드(Hotlinking) 차단 CDN 및 커뮤니티 사이트 (관련성 떨어지는 짤방 방지)
        'daumcdn.net', 'pstatic.net', 'tistory.com', 'blogfiles.naver.net', 
        'kakaocdn.net', 'namu.wiki', 'namu.la', 'dcinside', 'fmkorea', 'theqoo', 'ruliweb', 'inven',
        'tiktok.com', 'tiktokcdn.com', 'tiktokv.com', 'tiktok.net',
        'instagram.com', 'cdninstagram.com',
        'pinterest.com', 'pinimg.com', 'reddit.com', 'redditstatic.com', 'imgur.com',
        'fbcdn.net', 'twimg.com', 'shutterstock', 'istockphoto', 'gettyimages', 'alamy', 'freepik'
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
    주제 기반으로 Tavily에서 추가 이미지를 검색하여 fallback으로 사용합니다.
    크롤링+Tavily만으로 이미지를 확보합니다.
    
    Args:
        topic: 매거진 주제
        count: 필요한 이미지 수
    
    Returns:
        실제 사진 URL 리스트
    """
    # 주제 관련 이미지 검색 바리에이션
    search_variations = [
        f"{topic} 사진",
        f"{topic} 이미지 고화질",
        f"{topic} photography",
    ]
    
    results = []
    seen = set()
    
    for query in search_variations:
        if len(results) >= count:
            break
        try:
            _, imgs = search_with_tavily(query, topic=topic)
            for img in imgs:
                if img not in seen and validate_image_url(img):
                    seen.add(img)
                    results.append(img)
                    if len(results) >= count:
                        break
        except Exception as e:
            print(f"⚠️ Topic fallback search failed for '{query}': {e}")
    
    print(f"🎯 Topic fallback: {len(results)}/{count} REAL images via Tavily for '{topic}'")
    return results


def scrape_multiple_with_jina(urls: list, max_count: int = 3, request_state: dict = None) -> tuple:
    """
    상위 N개 URL을 순차 크롤링하여 이미지 풀을 최대한 확보합니다.
    
    Args:
        urls: 크롤링할 URL 리스트
        max_count: 최대 크롤링할 URL 수
        
    Returns:
        (deep_content, scraped_images) 튜플
        - deep_content: 첫 번째 성공한 크롤링 본문 (AI 프롬프트용)
        - scraped_images: 추출된 모든 이미지 URL 리스트 (중복 제거)
    """
    deep_content = ""
    scraped_images = []
    seen_images = set()
    
    for i, url in enumerate(urls[:max_count]):
        print(f"📖 Jina crawling [{i+1}/{min(len(urls), max_count)}]: {url[:80]}...")
        content = scrape_with_jina(url, request_state=request_state)
        if content:
            # 첫 번째 성공한 본문을 AI 프롬프트용으로 저장
            if not deep_content:
                deep_content = content
            
            # 이미지 추출 (중복 제거)
            images = extract_images_from_content(content)
            for img in images:
                if img not in seen_images:
                    seen_images.add(img)
                    scraped_images.append(img)
            
            print(f"  → {len(images)} images extracted (total unique: {len(scraped_images)})")
    
    print(f"📰 Multi-crawl complete: {len(scraped_images)} unique images from {min(len(urls), max_count)} URLs")
    return deep_content, scraped_images


# 이미지 유효성 검증 캐시 (동일 URL 반복 검증 방지)
_validation_cache = {}

def validate_image_url(url: str) -> bool:
    """
    HTTP HEAD 요청으로 이미지 URL의 유효성을 검증합니다.
    Content-Type이 image/*이고 status 200이면 유효.
    
    Args:
        url: 검증할 이미지 URL
        
    Returns:
        True: 유효한 이미지, False: 엑박/빈이미지/접근불가
    """
    if not url or not url.startswith('http'):
        return False
    
    # 캐시 확인
    if url in _validation_cache:
        return _validation_cache[url]
    
    try:
        response = requests.head(url, timeout=3, allow_redirects=True)
        content_type = response.headers.get('Content-Type', '').lower()
        content_length_str = response.headers.get('Content-Length', '0')
        
        # 크기 확인 (Content-Length가 제공될 경우)
        try:
            content_length = int(content_length_str)
        except ValueError:
            content_length = 5001 # 알 수 없는 경우 일단 통과
            
        is_valid = (
            response.status_code == 200 
            and content_type.startswith('image/')
        )
        
        if is_valid and content_length > 0 and content_length < 5000:
            print(f"➖ Image too small ({content_length} bytes), likely an icon: {url[:60]}...")
            is_valid = False
            
        if not is_valid and (response.status_code != 200 or not content_type.startswith('image/')):
            print(f"❌ Image validation failed: {url[:60]}... (status={response.status_code}, type={content_type})")
        
        _validation_cache[url] = is_valid
        return is_valid
        
    except Exception as e:
        print(f"❌ Image validation error: {url[:60]}... ({e})")
        _validation_cache[url] = False
        return False

def search_with_pexels(query: str, orientation: str = 'landscape', per_page: int = 5) -> list:
    """
    Pexels API를 사용하여 고품질 무료 스톡 이미지를 검색합니다.
    
    Args:
        query: 검색어 (영어가 가장 정확함)
        orientation: 이미지 방향 (landscape, portrait, square)
        per_page: 가져올 이미지 수
    
    Returns:
        이미지 URL 리스트 (large 사이즈)
    """
    api_key = getattr(settings, 'PEXELS_API_KEY', None)
    if not api_key:
        print("⚠️ PEXELS_API_KEY not configured")
        return []
        
    print(f"📸 Pexels Searching for: {query}")
    
    url = "https://api.pexels.com/v1/search"
    headers = {
        "Authorization": api_key
    }
    params = {
        "query": query,
        "orientation": orientation,
        "per_page": per_page
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        images = []
        for photo in data.get('photos', []):
            img_url = photo.get('src', {}).get('large')
            if img_url:
                images.append(img_url)
                
        print(f"✅ Pexels Found {len(images)} images")
        return images
    except Exception as e:
        print(f"❌ Pexels Error: {e}")
        return []

import concurrent.futures

def scrape_labeled_sources(urls: list, max_count: int = 9, request_state: dict = None) -> tuple:
    """
    [Parallel Scraping V2] Returns labeled source blocks per URL.
    Uses ThreadPoolExecutor to scrape multiple URLs concurrently.
    
    Returns:
        (labeled_sources, scraped_images) tuple
    """
    labeled_sources = []
    scraped_images = []
    seen_images = set()
    
    # Initial create_magazine uses fewer Jina reads for latency; env can tune.
    env_max_urls = int(os.getenv("JINA_MAX_URLS", str(max_count)))
    effective_max_count = max(1, min(max_count, env_max_urls))
    target_urls = urls[:effective_max_count]
    print(f"🚀 Parallel Scraping started for {len(target_urls)} URLs...")

    def scrape_job(url_info):
        idx, url = url_info
        content = scrape_with_jina(url, request_state=request_state)
        if content:
            return (idx, url, content)
        return (idx, url, None)

    results = []
    remaining_urls = list(enumerate(target_urls))
    if remaining_urls:
        # Probe the first URL before fan-out. If the configured Jina key has
        # insufficient balance, the request_state switches to no-auth and the
        # rest of this create_magazine request avoids repeated auth failures.
        results.append(scrape_job(remaining_urls.pop(0)))

    # Scrape remaining URLs in parallel after request-level auth state is known.
    if remaining_urls:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(remaining_urls)) as executor:
            results.extend(executor.map(scrape_job, remaining_urls))

    # Process and sort results by original index to keep Source 1, 2, 3... order
    results.sort(key=lambda x: x[0])

    for idx, url, content in results:
        if content:
            labeled_sources.append((url, content))
            images = extract_images_from_content(content)
            for img in images:
                if img not in seen_images:
                    seen_images.add(img)
                    scraped_images.append(img)
            print(f"  [Source {idx+1}] Success: {len(content)} chars, {len(images)} images")
        else:
            print(f"  [Source {idx+1}] Failed: {url[:60]}...")
    
    print(f"✅ Parallel Scraping complete: {len(labeled_sources)} sources, {len(scraped_images)} images")
    return labeled_sources, scraped_images
