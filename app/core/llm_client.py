import json
import logging
import os
import openai
import google.generativeai as genai
from app.config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.openai_client = None
        self.gemini_model = None
        self._initialize_clients()

    def _initialize_clients(self):
        # Initialize OpenAI if key exists (PRIORITY)
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
            try:
                self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("✅ OpenAI client initialized successfully.")
            except Exception as e:
                logger.error(f"❌ Failed to initialize OpenAI client: {e}")
        else:
            logger.warning("⚠️ OPENAI_API_KEY not set or empty. OpenAI will not be available.")

        # Initialize Gemini if key exists
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip():
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                # Try multiple model names in order of preference
                # Note: Use models that work with v1beta API
                # gemini-pro is the most stable and widely supported
                gemini_models = [
                    'gemini-1.5-flash',  # Fast, highly capable, follows instructions well
                    'gemini-1.5-pro',    # Most capable model
                    'gemini-pro',        # Legacy fallback
                ]
                
                for model_name in gemini_models:
                    try:
                        self.gemini_model = genai.GenerativeModel(model_name)
                        logger.info(f"✅ Gemini client initialized (model: {model_name}).")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to initialize {model_name}: {e}")
                        continue
                
                if not self.gemini_model:
                    logger.error(f"❌ All Gemini models failed. Tried: {gemini_models}")
                    logger.error("Please check your GEMINI_API_KEY and available models.")
                    logger.error("You can check available models at: https://ai.google.dev/models/gemini")
            except Exception as e:
                logger.error(f"❌ Failed to configure Gemini: {e}")
                self.gemini_model = None
        else:
            logger.info("ℹ️ GEMINI_API_KEY not set. Gemini will not be available.")

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """
        Generates text using the available LLM provider.
        Strategy: If Gemini is available, use it first (for users without OpenAI).
        Otherwise, use OpenAI as the standard/default.
        Falls back to the other if the first one fails.
        """
        # Strategy: If both are available, try Gemini first (for users who prefer Gemini)
        # If only one is available, use that one
        # If the first fails, fallback to the other
        
        # Try Gemini first if available (for users who have Gemini but not OpenAI)
        if self.gemini_model:
            try:
                # Re-initialize model with system_instruction for better directive adherence
                model_name = getattr(self.gemini_model, 'model_name', 'gemini-pro').split('/')[-1]
                model_with_instr = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_prompt
                )
                
                response = model_with_instr.generate_content(
                    user_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=8192
                    )
                )
                if not response.text:
                    raise ValueError("Gemini returned empty response")
                return response.text
            except Exception as e:
                logger.error(f"❌ Gemini generation failed: {e}")
                logger.info("Falling back to OpenAI...")

        # Fallback to OpenAI (standard/default) if Gemini failed or not available
        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"❌ OpenAI generation failed: {e}")
                raise e

        # No client available
        error_msg = "No LLM client configured. "
        if not settings.OPENAI_API_KEY or not settings.OPENAI_API_KEY.strip():
            error_msg += "OPENAI_API_KEY is missing or empty. "
        if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
            error_msg += "GEMINI_API_KEY is missing or empty. "
        error_msg += "Please set at least one API key in .env file."
        raise ValueError(error_msg)

    def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> dict:
        """
        Generates a JSON response and ensures it is valid.
        """
        text_response = self.generate_text(system_prompt, user_prompt, temperature)
        
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
