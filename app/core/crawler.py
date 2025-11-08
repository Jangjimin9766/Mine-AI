import requests
from bs4 import BeautifulSoup
# [수정] aiohttp 임포트 제거

def crawl_fashion_site(url: str) -> dict:
    """
    지정된 URL의 웹사이트를 크롤링하여 기본 정보를 반환합니다. (간단 예시)
    """
    print(f"Starting crawl for: {url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        # [수정] aiohttp 대신 requests 사용
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = soup.find('title').get_text(strip=True) if soup.find('title') else 'No Title Found'
        
        return {"url": url, "title": title, "content_snippet": "..."}
    
    except requests.RequestException as e:
        print(f"Error during crawling: {e}")
        return {"url": url, "error": str(e)}