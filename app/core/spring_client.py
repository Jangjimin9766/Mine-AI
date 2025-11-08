import requests
from app.config import settings

def get_user_data_from_spring(user_id: str) -> dict:
    """
    Spring Boot 서버 API를 호출하여 특정 유저의 데이터를 가져옵니다.
    (예: 컬렉션, 무드보드 정보)
    """
    # (내부 API 엔드포인트는 Spring 서버와 협의 필요)
    api_url = f"{settings.SPRING_API_URL}/api/internal/users/{user_id}/data"
    
    print(f"Requesting data for user {user_id} from Spring: {api_url}")
    
    try:
        # (Spring 서버와 인증 토큰을 주고받는 로직이 추가될 수 있음)
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()  # 200번대가 아니면 에러
        return response.json()
    
    except requests.RequestException as e:
        print(f"Error fetching data from Spring server: {e}")
        # 실패 시 에러 대신 기본 데이터 반환
        return {"error": "Could not fetch user data from Spring", "details": str(e)}