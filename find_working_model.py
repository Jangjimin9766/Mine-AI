import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

models_to_test = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro",
    "gemini-1.5-pro-latest",
    "gemini-pro",
    "gemini-flash-latest",
    "gemini-2.0-flash-exp"
]

print("Starting model connectivity test...")
for model_name in models_to_test:
    try:
        print(f"Testing {model_name}...", end=" ")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say 'Hello'", generation_config={"max_output_tokens": 10})
        print(f"✅ Success: {response.text.strip()}")
        print(f"\nFOUND WORKING MODEL: {model_name}")
        # Stop at the first working one
        break
    except Exception as e:
        print(f"❌ Failed: {type(e).__name__}")
