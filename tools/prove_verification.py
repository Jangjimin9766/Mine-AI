import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai
import json

load_dotenv()

def prove_verification():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env")
        return

    genai.configure(api_key=api_key)
    
    models_to_try = [
        'gemini-1.5-flash', 
        'gemini-1.5-flash-latest', 
        'gemini-1.5-pro',
        'gemini-2.0-flash-exp',
        'gemini-pro'
    ]
    
    model = None
    for model_name in models_to_try:
        try:
            print(f"Trying model: {model_name}...")
            test_model = genai.GenerativeModel(model_name)
            # Test call to verify model
            test_model.generate_content("test", generation_config={"max_output_tokens": 1})
            model = test_model
            print(f"Successfully selected model: {model_name}\n")
            break
        except Exception as e:
            print(f"Failed to use model {model_name}: {e}")
            continue

    if not model:
        print("Error: Could not find any working Gemini model.")
        return

    test_cases = [
        {"topic": "리락쿠마", "prompt": "A cute brown teddy bear plushie sitting on a chair, Japanese aesthetic."},
        {"topic": "리락쿠마", "prompt": "A beautiful Japanese woman wearing a traditional kimono in a zen garden."},
        {"topic": "나파 밸리 와인", "prompt": "A glass of red wine on a wooden table with vineyards in the background."},
    ]

    print("\n--- [M+MAC Verification Feasibility Test] ---")
    
    for case in test_cases:
        M = case["topic"]
        MAC = case["prompt"]
        
        system_instruction = f"""
        당신은 이미지 프롬프트 검증기입니다. 
        사용자의 원래 주제(Topic)와 생성된 이미지 프롬프트(Prompt)를 비교하여 
        프롬프트가 주제의 핵심을 잘 유지하고 있는지 점수를 매기세요.
        
        - 주제: {M}
        - 프롬프트: {MAC}
        
        결과는 반드시 다음 JSON 형식으로만 응답하세요:
        {{
            "relevance_score": (0.0에서 1.0 사이의 실수),
            "reason": "(한글로 된 이유 설명)",
            "detected_subject": "(프롬프트에서 파악한 실제 주인공)"
        }}
        """
        
        response = model.generate_content(system_instruction)
        try:
            # Simple JSON extraction
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            result = json.loads(text)
            
            print(f"\n[주제(M)]: {M}")
            print(f"[프롬프트(MAC)]: {MAC}")
            print(f" > 판정 결과: {result['relevance_score']}")
            print(f" > 파악된 주인공: {result['detected_subject']}")
            print(f" > 사유: {result['reason']}")
            
            if result['relevance_score'] >= 0.7:
                print(" ✅ [PASS] 무결성 확인됨")
            else:
                print(" ❌ [FAIL] 무결성 위배 (재생성 필요)")
                
        except Exception as e:
            print(f"Error parsing response: {e}")
            print(f"Raw response: {response.text}")

if __name__ == "__main__":
    prove_verification()
