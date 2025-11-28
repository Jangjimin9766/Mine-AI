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

def save_magazine_to_spring(magazine_data: dict, user_email: str) -> bool:
    """
    [New] 생성된 매거진 JSON 데이터를 Spring Boot 서버로 전송하여 저장합니다.
    """
    # Spring Controller에 만들어둔 주소: /api/internal/magazine
    api_url = f"{settings.SPRING_API_URL}/api/internal/magazine"
    
    print(f"🚚 Sending Magazine Data to Spring: {api_url} (User: {user_email})")
    
    # Spring 서버의 MagazineCreateRequest DTO 구조에 맞춰서 데이터 구성 (Flat Structure)
    # magazine_data에 있는 title, introduction, sections 등을 그대로 쓰고, user_email만 추가
    payload = magazine_data.copy()
    payload["user_email"] = user_email
    
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status() # 200 OK 아니면 에러 발생
        
        print(f"✅ Successfully saved to Spring! Response: {response.text}")
        return True
        
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        print(f"❌ Failed to save magazine to Spring (Status: {status_code})")
        
        if status_code == 403:
            print("💡 Tip: 403 Forbidden - Spring Security 설정이나 '존재하지 않는 사용자' 문제일 수 있습니다.")
            print("   -> Spring DB에 해당 이메일의 유저가 있는지 확인해보세요.")
        elif status_code == 500:
            print("💡 Tip: 500 Internal Server Error - Spring 서버 내부 오류입니다.")
            print("   -> 유저 이메일이 DB에 없어서 발생했을 가능성이 높습니다.")
            
        return False
    except Exception as e:
        print(f"❌ Failed to save magazine to Spring: {e}")
        return False