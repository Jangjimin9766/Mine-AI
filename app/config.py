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

    OPENAI_API_KEY: str
    SPRING_API_URL: str = "http://localhost:8080"

# 어디서든 import 해서 사용할 수 있도록 객체 생성
settings = Settings()