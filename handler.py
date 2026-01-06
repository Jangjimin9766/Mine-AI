"""
RunPod Serverless Handler for M:ine AI Server
Converts FastAPI endpoints to RunPod serverless format.
# Rebuild trigger: 2026-01-04-v2 - Diagnose worker crash
"""
print("=" * 50)
print("🔧 handler.py is loading...")
print("=" * 50)

import runpod
import os
import json
import traceback
import sys

print(f"✅ Basic imports done. Python: {sys.version}")
print(f"✅ Working directory: {os.getcwd()}")

# Test critical imports BEFORE handler runs
try:
    print("📦 Testing app.core imports...")
    from app.core.llm_client import llm_client
    print("✅ llm_client imported")
except Exception as e:
    print(f"❌ llm_client import failed: {e}")
    print(traceback.format_exc())

try:
    print("📦 Testing local_diffusion_client import...")
    from app.core.local_diffusion_client import local_diffusion_client
    print("✅ local_diffusion_client imported")
except Exception as e:
    print(f"❌ local_diffusion_client import failed: {e}")
    print(traceback.format_exc())

print("=" * 50)
print("🎯 All imports completed, defining handler...")
print("=" * 50)

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
        elif action == "create_moodboard" or action == "generate_moodboard":
            return handle_create_moodboard(data)
        elif action == "edit_magazine" or action == "chat":
            return handle_edit_magazine(data)
        elif action == "health":
            return {"status": "healthy", "message": "M:ine AI Serverless is running"}
        else:
            return {"error": f"Unknown action: {action}"}
            
    except Exception as e:
        print(f"❌ Handler Error: {e}")
        print(f"📋 Full Traceback:\n{traceback.format_exc()}")
        return {"error": str(e), "traceback": traceback.format_exc()}


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
    print("🎨 [1/4] Moodboard handler started")
    print(f"🎨 [1/4] Data received: {data}")
    
    try:
        print("🎨 [2/4] Importing generate_moodboard...")
        from app.core.moodboard_maker import generate_moodboard
        print("🎨 [2/4] Import successful")
        
        print("🎨 [3/4] Calling generate_moodboard...")
        result = generate_moodboard(
            topic=data.get("topic"),
            user_mood=data.get("user_mood"),
            user_interests=data.get("user_interests"),
            magazine_tags=data.get("magazine_tags"),
            magazine_titles=data.get("magazine_titles")
        )
        print(f"🎨 [4/4] Result: {result is not None}")
        
        if not result:
            print("🎨 [4/4] Result is None, returning error")
            return {"error": "Failed to generate moodboard"}
        
        print("🎨 [4/4] Success! Returning result")
        return result
        
    except Exception as e:
        print(f"❌ Moodboard Error: {e}")
        print(f"📋 Traceback:\n{traceback.format_exc()}")
        return {"error": str(e), "traceback": traceback.format_exc()}


def handle_edit_magazine(data: dict) -> dict:
    """
    Handle magazine editing/chat request.
    Uses magazine_editor to modify existing magazines based on user instructions.
    """
    print("💬 [1/4] Edit magazine handler started")
    print(f"💬 [1/4] Data received: {data}")
    
    try:
        from app.core.magazine_editor import (
            analyze_user_intent,
            regenerate_section,
            add_new_section,
            change_overall_tone
        )
        print("💬 [2/4] Imports successful")
        
        message = data.get("message", "")
        magazine_data = data.get("magazine_data", {})
        
        if not message:
            return {"error": "message is required"}
        if not magazine_data:
            return {"error": "magazine_data is required"}
        
        print(f"💬 [3/4] Analyzing intent for: {message[:50]}...")
        
        # 1. 사용자 의도 분석
        intent = analyze_user_intent(message, magazine_data)
        print(f"💬 [3/4] Intent: {intent}")
        
        # 2. 의도에 따른 처리
        result = None
        if intent.intent_type == "regenerate_section":
            result = regenerate_section(
                magazine_data,
                intent.target_section_index,
                intent.instruction
            )
        elif intent.intent_type == "add_section":
            result = add_new_section(magazine_data, intent.instruction)
        elif intent.intent_type == "change_tone":
            result = change_overall_tone(magazine_data, intent.instruction)
        else:
            # 기본: 전체 톤 변경으로 처리
            result = change_overall_tone(magazine_data, message)
        
        print(f"💬 [4/4] Result: {result is not None}")
        
        if not result:
            return {"error": "Failed to edit magazine"}
        
        return {
            "success": True,
            "intent": intent.intent_type if intent else "general",
            "updated_magazine": result
        }
        
    except Exception as e:
        print(f"❌ Edit Magazine Error: {e}")
        print(f"📋 Traceback:\n{traceback.format_exc()}")
        return {"error": str(e), "traceback": traceback.format_exc()}


# Start the RunPod serverless worker
if __name__ == "__main__":
    print("🎯 Starting M:ine AI Serverless Worker...")
    runpod.serverless.start({"handler": handler})
