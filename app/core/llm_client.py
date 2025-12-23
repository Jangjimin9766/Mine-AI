from openai import OpenAI
from app.config import settings
import json

class LLMClient:
    def __init__(self):
        # 지연 초기화를 위해 None으로 시작
        self._client = None
        self.default_model = "gpt-3.5-turbo"

    def _get_client(self):
        """OpenAI 클라이언트를 지연 초기화하여 반환"""
        if self._client is None:
            api_key = settings.OPENAI_API_KEY
            if not api_key or api_key == "test-key":
                return None  # 테스트 환경에서는 None 반환
            self._client = OpenAI(api_key=api_key)
        return self._client

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """
        일반적인 텍스트 생성 (요약, 채팅, 태깅 등)
        """
        client = self._get_client()
        if client is None:
            print("⚠️ OpenAI API key not configured")
            return ""
        
        try:
            response = client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ LLM Text Generation Error: {e}")
            return ""

    def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> dict:
        """
        JSON 포맷 강제 생성 (매거진 데이터 생성용)
        """
        client = self._get_client()
        if client is None:
            print("⚠️ OpenAI API key not configured")
            return {}
        
        try:
            response = client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"❌ LLM JSON Generation Error: {e}")
            return {}

# 싱글톤 인스턴스 생성 (어디서든 llm_client만 임포트하면 됨)
llm_client = LLMClient()