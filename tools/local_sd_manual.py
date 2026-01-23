import requests
import base64
import json
import time

def test_local_generation():
    url = "http://localhost:8000/api/magazine/moodboard"
    
    payload = {
        "topic": "Cozy Winter Morning",
        "user_mood": "Warm, Relaxing",
        "user_interests": ["Coffee", "Jazz", "Books"],
        "magazine_tags": ["Interior", "Lifestyle"],
        "magazine_titles": ["Winter Home Decor"]
    }
    
    print(f"🚀 Requesting Moodboard Generation for: {payload['topic']}")
    print("⏳ This may take a while (Model Download + Generation)...")
    
    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=600) # 10분 타임아웃 (첫 다운로드 고려)
        
        if response.status_code == 200:
            data = response.json()
            image_data = data["image_url"]
            description = data["description"]
            
            # Remove header if present
            if "base64," in image_data:
                image_data = image_data.split("base64,")[1]
            
            # Save image
            with open("test_output.png", "wb") as f:
                f.write(base64.b64decode(image_data))
                
            elapsed = time.time() - start_time
            print(f"✅ Success! Image saved to 'test_output.png'")
            print(f"⏱️ Time taken: {elapsed:.2f} seconds")
            print(f"📝 Prompt used: {description}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    # 서버가 뜰 때까지 잠시 대기
    time.sleep(5)
    test_local_generation()
