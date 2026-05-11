import json
import logging
import openai
from app.config import settings

logger = logging.getLogger(__name__)


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
        self.openai_client = None
        self.call_count = 0
        self._initialize_clients()

    def _initialize_clients(self):
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
            try:
                self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("✅ OpenAI client initialized successfully.")
            except Exception as e:
                logger.error(f"❌ Failed to initialize OpenAI client: {e}")
        else:
            logger.warning("⚠️ OPENAI_API_KEY not set or empty. OpenAI will not be available.")

    def is_configured(self) -> bool:
        """OpenAI API 키가 올바르게 설정되어 있는지 확인"""
        return bool(self.openai_client)

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, response_format: dict = None) -> str:
        """
        Generates text using OpenAI only.
        """
        self.call_count += 1

        if self.openai_client:
            try:
                request_kwargs = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": 16000,
                }
                if response_format:
                    request_kwargs["response_format"] = response_format
                response = self.openai_client.chat.completions.create(**request_kwargs)
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"❌ OpenAI generation failed: {e}")
                raise e

        raise APIKeyNotConfiguredError("OPENAI_API_KEY is missing or empty.")

    def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, response_format: dict = None) -> dict:
        """
        Generates a JSON response and ensures it is valid.
        """
        text_response = self.generate_text(
            system_prompt,
            user_prompt,
            temperature,
            response_format=response_format or {"type": "json_object"},
        )
        
        # Strip markdown code blocks if present
        cleaned_response = text_response.strip()
        if "```" in cleaned_response:
            # Handle ```json ... ``` or just ``` ... ```
            import re
            json_pattern = r"```(?:json)?\s*(.*?)\s*```"
            match = re.search(json_pattern, cleaned_response, re.DOTALL)
            if match:
                cleaned_response = match.group(1)
            else:
                # Fallback: remove symbols manually if regex fails
                cleaned_response = cleaned_response.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response. Raw output: {text_response}")
            # Final attempt: extract anything that looks like a JSON object
            try:
                import re
                json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except:
                pass
            raise e

# Export a single instance
llm_client = LLMClient()
