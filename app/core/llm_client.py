import google.generativeai as genai
from app.config import settings
import json

class LLMClient:
    def __init__(self):
        # 지연 초기화를 위해 None으로 시작
        self._model = None
        self.default_model = "gemini-flash-latest" # 검증된 최신 Flash 모델명

    def _get_model(self):
        """Gemini 모델을 지연 초기화하여 반환"""
        if self._model is None:
            api_key = settings.GEMINI_API_KEY
            if not api_key:
                print("⚠️ Gemini API key not configured")
                return None
            
            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel(self.default_model)
        return self._model

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """
        일반적인 텍스트 생성 (요약, 채팅, 태깅 등)
        """
        model = self._get_model()
        if model is None:
            return ""
        
        try:
            full_prompt = f"{system_prompt}\n\nUser: {user_prompt}"
            
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                )
            )
            return response.text.strip()
        except Exception as e:
            print(f"❌ Gemini Text Generation Error: {e}")
            return ""

    def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> dict:
        """
        JSON 포맷 강제 생성 (매거진 데이터 생성용)
        """
        model = self._get_model()
        if model is None:
            return {}
        
        try:
            full_prompt = f"{system_prompt}\n\nPlease output ONLY valid JSON.\n\nUser: {user_prompt}"
            
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    response_mime_type="application/json"
                )
            )
            
            content = response.text
            return json.loads(content)
        except Exception as e:
            print(f"❌ Gemini JSON Generation Error: {e}")
            return {}

# 싱글톤 인스턴스 생성 (어디서든 llm_client만 임포트하면 됨)
llm_client = LLMClient()
