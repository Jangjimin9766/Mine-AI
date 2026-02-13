import google.generativeai as genai
import os
import time
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

def test_model(model_name):
    print(f"\n🎬 Testing generation with: {model_name}")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello")
        if response.text:
            print(f"✅ Success! Response received.")
            return True
    except Exception as e:
        if "429" in str(e):
            print(f"❌ Rate Limit (429): {e}")
        else:
            print(f"❌ Failed: {e}")
        return False

if not api_key:
    print("❌ GEMINI_API_KEY not found in .env")
else:
    genai.configure(api_key=api_key)
    # 넓은 범위의 모델들을 모두 테스트
    models_to_test = [
        'gemini-1.5-flash', 
        'gemini-1.5-pro', 
        'gemini-2.0-flash', 
        'gemini-pro'
    ]
    
    working_models = []
    for m in models_to_test:
        if test_model(m):
            working_models.append(m)
        time.sleep(2) # 짧은 대기
    
    if working_models:
        print(f"\n✨ Working models found: {working_models}")
    else:
        print("\n🚫 No working models found for this API key. Please check your AI Studio billing/project settings.")
