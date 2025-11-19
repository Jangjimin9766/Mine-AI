import requests
from bs4 import BeautifulSoup

def crawl_fashion_site(url: str) -> dict:
    """
    주어진 URL에서 제목, 본문 텍스트, 메인 이미지를 추출합니다.
    """
    print(f"🕸️ Starting crawl for: {url}")
    
    # 1. 봇 탐지를 피하기 위한 헤더 설정 (마치 웹브라우저인 척하기)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        # 2. HTML 요청
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # 200 OK가 아니면 에러 발생
        
        # 3. 파싱 (HTML 분석)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # --- 데이터 추출 로직 (사이트마다 구조가 다를 수 있음 - 일반적인 구조 기준) ---
        
        # [제목] h1 태그 또는 title 태그
        title_tag = soup.find('h1')
        if not title_tag:
            title_tag = soup.find('title')
        title = title_tag.get_text(strip=True) if title_tag else "No Title"

        # [본문] p 태그들을 모아서 하나의 텍스트로 합침
        paragraphs = soup.find_all('p')
        content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 10])
        # 본문이 너무 길면 500자만 자르기 (테스트용)
        content_snippet = content[:500] + "..." if len(content) > 500 else content

        # [이미지] og:image (SNS 공유용 썸네일)가 가장 퀄리티가 좋음
        image_url = ""
        og_image = soup.find('meta', property='og:image')
        if og_image:
            image_url = og_image.get('content')
        
        print(f"✅ Crawl success: {title}")

        return {
            "status": "success",
            "url": url,
            "title": title,
            "image_url": image_url,
            "content": content_snippet, # 요약 및 태깅에 사용할 본문
            "full_content": content     # 전체 본문 (필요시 사용)
        }
    
    except Exception as e:
        print(f"❌ Error during crawling: {e}")
        return {
            "status": "fail",
            "url": url,
            "error": str(e)
        }