import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

models_to_test = [
    "gemini-flash-latest",
    "gemini-pro-latest",
    "gemini-2.0-flash-exp",
    "gemini-2.5-flash"
]

print("Starting connectivity test with exact names...")
for model_name in models_to_test:
    try:
        print(f"Testing {model_name}...", end=" ")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say Hello", generation_config={"max_output_tokens": 10})
        print("Success!")
        print(f"WINNER: {model_name}")
        # Write the winner to a temp file so Antigravity can read it easily
        with open('working_model.txt', 'w') as sf:
            sf.write(model_name)
        break
    except Exception as e:
        print(f"Failed: {type(e).__name__}")
