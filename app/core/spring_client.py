import requests
from app.config import settings

def get_user_data_from_spring(user_id: str) -> dict:
    """
    (기존 함수) Spring Boot 서버에서 유저 데이터 가져오기
    """
    api_url = f"{settings.SPRING_API_URL}/api/internal/users/{user_id}/data"
    try:
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"⚠️ Failed to fetch user data: {e}")
        return {}

def save_magazine_to_spring(magazine_data: dict) -> bool:
    """
    [New] 생성된 매거진 JSON 데이터를 Spring Boot 서버로 전송하여 저장합니다.
    """
    # Spring Controller에 만들어둔 주소: /api/internal/magazine
    api_url = f"{settings.SPRING_API_URL}/api/internal/magazine"
    
    print(f"🚚 Sending Magazine Data to Spring: {api_url}")
    
    try:
        response = requests.post(api_url, json=magazine_data, timeout=10)
        response.raise_for_status() # 200 OK 아니면 에러 발생
        
        print(f"✅ Successfully saved to Spring! Response: {response.text}")
        return True
        
    except requests.RequestException as e:
        print(f"❌ Failed to save magazine to Spring: {e}")
        # (중요) 실패했다고 AI 서버가 멈추면 안 됨. 로그만 남기고 False 반환
        return False