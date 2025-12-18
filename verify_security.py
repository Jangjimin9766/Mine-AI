import requests
import time

BASE_URL = "http://localhost:8000"
API_KEY = "mine-secret-key-1234"

def test_security():
    print("🔐 Testing API Security...")
    
    # 1. Without Key (Should Fail)
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
             print("✅ Health check is public (OK)")
        else:
             print(f"❌ Health check failed: {response.status_code}")
             
        # Try a protected endpoint without key
        response = requests.post(f"{BASE_URL}/api/magazine/create", json={})
        if response.status_code == 403:
            print("✅ Protected endpoint blocked without key (OK)")
        else:
            print(f"❌ Protected endpoint NOT blocked: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ Server is not running? {e}")

    # 2. With Key (Should Pass)
    headers = {"X-API-KEY": API_KEY}
    payload = {
        "topic": "Security Test",
        "user_interests": ["test"]
    }
    
    # We won't actually wait for generation, just check if we get past auth
    # For this test to really work without waiting for full generation, 
    # we might just hit a lighter endpoint or expect a Validation Error (422) instead of 403
    print("\n🔑 Testing with Valid Key...")
    response = requests.post(f"{BASE_URL}/api/magazine/create", json=payload, headers=headers)
    
    if response.status_code == 403:
        print("❌ Key rejected (Failed)")
    elif response.status_code in [200, 422, 500]: 
        # 422 means authentication passed but validation failed (which is good for this test)
        # 500 might mean internal error but auth passed
        print(f"✅ Key accepted (Status: {response.status_code})")
    else:
        print(f"❓ Unexpected status: {response.status_code}")

if __name__ == "__main__":
    test_security()
