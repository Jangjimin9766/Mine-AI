from openai import OpenAI
from app.config import settings

class GroqClient:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.base_url = "https://api.groq.com/openai/v1"
        self.client = None
        
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

    def generate_json(self, system_prompt: str, user_prompt: str, model: str = "llama-3.3-70b-versatile") -> dict:
        """
        Generate JSON output using Groq/Llama.
        """
        if not self.client:
            print("Warning: Groq API key not configured.")
            return None

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            import json
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Groq API Error: {e}")
            return None

groq_client = GroqClient()
