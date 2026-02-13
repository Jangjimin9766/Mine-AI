import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add app directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.moodboard_maker import verify_prompt_integrity, generate_moodboard_prompt
from app.core.llm_client import llm_client

def test_mac_verification():
    print("\n--- [M+MAC Logic Verification Test] ---")
    
    test_cases = [
        {
            "topic": "리락쿠마",
            "description": "정상적인 경우 (리락쿠마 포함)"
        },
        {
            "topic": "리락쿠마",
            "description": "환각 발생 상황 시뮬레이션 (기모노 여성)",
            "forced_MAC": "A beautiful Japanese woman in a traditional silk kimono, standing in a peaceful zen garden, soft cinematic lighting, 8k masterpiece."
        }
    ]

    for case in test_cases:
        print(f"\n[Case]: {case['description']}")
        topic = case["topic"]
        
        if "forced_MAC" in case:
            mac = case["forced_MAC"]
        else:
            print(f" > Generating MAC for Topic: {topic}...")
            mac = generate_moodboard_prompt(topic=topic)
            
        print(f" > MAC (Prompt): {mac}")
        
        print(" > Running Verifier...")
        result = verify_prompt_integrity(topic, mac)
        
        print(f" > Score: {result['score']}")
        print(f" > Reason: {result['reason']}")
        
        if result['is_valid']:
            print(" [PASS] VERIFICATION PASSED")
        else:
            print(" [FAIL] VERIFICATION FAILED (System correctly caught the integrity violation)")

if __name__ == "__main__":
    test_mac_verification()
