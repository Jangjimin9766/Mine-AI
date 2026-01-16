import requests
import json

BASE_URL = "http://localhost:8000/api/magazine"
HEADERS = {
    "x-api-key": "mine-secret-key-1234",
    "Content-Type": "application/json"
}

def test_moodboard():
    payload = {
        "topic": "Cozy winter cabin",
        "user_mood": "Warm and peaceful",
        "user_interests": ["Interior design", "Photography"],
        "magazine_tags": ["Winter", "Cozy"],
        "magazine_titles": ["Winter Dreams"]
    }
    
    print("Testing Moodboard Generation...")
    try:
        response = requests.post(f"{BASE_URL}/moodboard", headers=HEADERS, json=payload, timeout=120)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"Description: {result.get('description')}")
            print(f"Image URL (Base64 length): {len(result.get('image_url'))}")
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_moodboard()
