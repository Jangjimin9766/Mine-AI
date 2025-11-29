from openai import OpenAI
from app.config import settings
import json

class LLMClient:
    def __init__(self):
        # 지금은 OpenAI를 쓰지만, 나중엔 여기서 로컬 모델을 로드할 수도 있습니다.
        # self.local_model = load_lora_model(...) 
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.default_model = "gpt-3.5-turbo"

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """
        일반적인 텍스트 생성 (요약, 채팅, 태깅 등)
        """
        try:
            # [확장 포인트] 나중에 model_type 인자를 받아서 분기 처리 가능
            # if model_type == 'local_lora': return self._call_local_model(...)
            
            response = self.client.chat.completions.create(
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
        try:
            response = self.client.chat.completions.create(
                model=self.default_model, # JSON 모드는 1106 버전 이상 권장되나 3.5-turbo 최신도 지원함
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                response_format={"type": "json_object"} # OpenAI 전용 JSON 모드
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"❌ LLM JSON Generation Error: {e}")
            return {}

    def generate_image(self, prompt: str, size: str = "1024x1024", quality: str = "standard") -> str:
        """
        DALL-E 3를 사용한 이미지 생성
        """
        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
            )
            return response.data[0].url
        except Exception as e:
            print(f"❌ LLM Image Generation Error: {e}")
            return ""

# 싱글톤 인스턴스 생성 (어디서든 llm_client만 임포트하면 됨)
llm_client = LLMClient()