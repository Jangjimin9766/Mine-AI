from openai import OpenAI
from app.config import settings
import json
import traceback


# ========== Custom Exceptions ==========
class LLMClientError(Exception):
    """LLM 클라이언트 관련 기본 예외"""
    pass

class APIKeyNotConfiguredError(LLMClientError):
    """API 키가 설정되지 않았을 때 발생"""
    pass

class LLMGenerationError(LLMClientError):
    """LLM 응답 생성 실패 시 발생"""
    pass


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
    
    def is_configured(self) -> bool:
        """API 키가 올바르게 설정되어 있는지 확인"""
        api_key = settings.OPENAI_API_KEY
        return api_key and api_key != "test-key"

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, raise_on_error: bool = False) -> str:
        """
        일반적인 텍스트 생성 (요약, 채팅, 태깅 등)
        
        Args:
            raise_on_error: True이면 에러 발생 시 예외를 던짐. False이면 빈 문자열 반환.
        """
        client = self._get_client()
        if client is None:
            error_msg = "OpenAI API key not configured. Check OPENAI_API_KEY in .env"
            print(f"⚠️ {error_msg}")
            if raise_on_error:
                raise APIKeyNotConfiguredError(error_msg)
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
            result = response.choices[0].message.content.strip()
            if not result:
                print("⚠️ LLM returned empty response")
            return result
        except Exception as e:
            error_msg = f"LLM Text Generation Error: {e}"
            print(f"❌ {error_msg}")
            print(f"📋 Traceback: {traceback.format_exc()}")
            if raise_on_error:
                raise LLMGenerationError(error_msg) from e
            return ""

    def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, raise_on_error: bool = False) -> dict:
        """
        JSON 포맷 강제 생성 (매거진 데이터 생성용)
        
        Args:
            raise_on_error: True이면 에러 발생 시 예외를 던짐. False이면 빈 딕셔너리 반환.
        """
        client = self._get_client()
        if client is None:
            error_msg = "OpenAI API key not configured. Check OPENAI_API_KEY in .env"
            print(f"⚠️ {error_msg}")
            if raise_on_error:
                raise APIKeyNotConfiguredError(error_msg)
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
            if not content:
                print("⚠️ LLM returned empty JSON response")
                if raise_on_error:
                    raise LLMGenerationError("LLM returned empty JSON response")
                return {}
            
            result = json.loads(content)
            return result
        except json.JSONDecodeError as e:
            error_msg = f"LLM JSON Parse Error: {e}"
            print(f"❌ {error_msg}")
            print(f"📋 Raw content: {content[:500] if content else 'None'}")
            if raise_on_error:
                raise LLMGenerationError(error_msg) from e
            return {}
        except Exception as e:
            error_msg = f"LLM JSON Generation Error: {e}"
            print(f"❌ {error_msg}")
            print(f"📋 Traceback: {traceback.format_exc()}")
            if raise_on_error:
                raise LLMGenerationError(error_msg) from e
            return {}


# 싱글톤 인스턴스 생성 (어디서든 llm_client만 임포트하면 됨)
llm_client = LLMClient()