from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    .env 파일에서 환경 변수를 읽어오는 설정 클래스
    """
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding='utf-8', 
        extra='ignore'
    )

    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    SPRING_API_URL: str = "http://localhost:8080"
    
    # 검색용 키 추가
    TAVILY_API_KEY: str = ""
    JINA_API_KEY: str = ""  # 선택 사항이라 기본값 비워둠
    UNSPLASH_ACCESS_KEY: str = ""  # 추후 사용 시 대비 (현재는 Pexels 메인)
    PEXELS_API_KEY: str = "" # Pexels 이미지 검색 API 키
    
    # 보안 키
    PYTHON_API_KEY: str = "mine-secret-key-1234"

    # Mine-server internal API key (X-Internal-Key)
    # Must match EC2 `/opt/mine/.env` value.
    MINE_INTERNAL_SECRET_KEY: str = ""
    
    # Logtail (Better Stack) 로깅
    LOGTAIL_SOURCE_TOKEN: str = ""  # Better Stack에서 발급받은 토큰
    LOGTAIL_HOST: str = "s1876389.eu-nbg-2.betterstackdata.com"  # Ingesting host

settings = Settings()
