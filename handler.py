"""
RunPod Serverless Handler for M:ine AI Server
Converts FastAPI endpoints to RunPod serverless format.
# Rebuild trigger: 2026-01-01 - x86_64 architecture fix
"""
import runpod
import os
import json

# Ensure environment variables are set for API clients
# These will be passed via RunPod's environment configuration

def handler(event):
    """
    Main handler for RunPod Serverless.
    
    Expected input format:
    {
        "input": {
            "action": "create_magazine" | "create_moodboard",
            "data": { ... request payload ... }
        }
    }
    """
    try:
        input_data = event.get("input", {})
        action = input_data.get("action")
        data = input_data.get("data", {})
        
        print(f"🚀 RunPod Handler received action: {action}")
        
        if action == "create_magazine":
            return handle_create_magazine(data)
        elif action == "create_moodboard":
            return handle_create_moodboard(data)
        elif action == "health":
            return {"status": "healthy", "message": "M:ine AI Serverless is running"}
        else:
            return {"error": f"Unknown action: {action}"}
            
    except Exception as e:
        print(f"❌ Handler Error: {e}")
        return {"error": str(e)}


def handle_create_magazine(data: dict) -> dict:
    """
    Handle magazine creation request.
    """
    from app.core.magazine_maker import generate_magazine_content
    
    topic = data.get("topic")
    user_interests = data.get("user_interests", [])
    
    if not topic:
        return {"error": "topic is required"}
    
    print(f"📰 Creating magazine for topic: {topic}")
    
    result = generate_magazine_content(
        topic=topic,
        user_interests=user_interests
    )
    
    if not result:
        return {"error": "Failed to generate magazine"}
    
    return result


def handle_create_moodboard(data: dict) -> dict:
    """
    Handle moodboard creation request.
    """
    from app.core.moodboard_maker import generate_moodboard
    
    result = generate_moodboard(
        topic=data.get("topic"),
        user_mood=data.get("user_mood"),
        user_interests=data.get("user_interests"),
        magazine_tags=data.get("magazine_tags"),
        magazine_titles=data.get("magazine_titles")
    )
    
    if not result:
        return {"error": "Failed to generate moodboard"}
    
    return result


# Start the RunPod serverless worker
if __name__ == "__main__":
    print("🎯 Starting M:ine AI Serverless Worker...")
    runpod.serverless.start({"handler": handler})
