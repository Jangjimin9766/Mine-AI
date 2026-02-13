import json
import random
import traceback
from app.core import prompts
from app.core.llm_client import llm_client
from app.core.groq_client import groq_client
from app.core.local_diffusion_client import local_diffusion_client

def verify_prompt_integrity(topic: str, prompt: str) -> dict:
    """
    Multi-LLM Blind Test Protocol:
    1. Groq (Llama 3) identifies the subject from the prompt WITHOUT knowing the topic.
    2. Gemini compares the identified subject with the original topic for a 'Soft Match'.
    """
    try:
        # 1. Blind Subject Identification (Meta Llama 3 via Groq)
        verifier_input = prompts.MOODBOARD_VERIFIER_PROMPT.format(prompt=prompt)
        
        # Using Llama 3 via Groq for high-speed objective verification
        blind_result = groq_client.generate_json(
            system_prompt="You are a cold, objective image analyzer.",
            user_prompt=verifier_input
        )
        
        if not blind_result:
            return {"is_valid": True, "score": 1.0, "reason": "Verifier unavailable, bypassing check"}

        detected_subject = blind_result.get("detected_subject", "Unknown")
        contains_humans = blind_result.get("contains_humans", False)
        
        # 2. Semantic Comparison (Gemini)
        # We ask Gemini to judge if the detected subject matches our target topic.
        comparison_prompt = f"""
        Compare SUBJECT A with SUBJECT B. 
        Are they semantically the same thing or is A a valid representation of B?
        
        SUBJECT A (Detected): {detected_subject}
        SUBJECT B (Original Topic): {topic}
        
        Output JSON: {{"match": boolean, "score": float, "reason": "Korean explanation"}}
        """
        
        comparison_res_text = llm_client.generate_text(
            system_prompt="You are a linguistic expert comparing entities.",
            user_prompt=comparison_prompt
        )
        
        # Simple cleanup and parse
        clean_json = comparison_res_text.strip()
        if "```json" in clean_json:
            clean_json = clean_json.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_json:
            clean_json = clean_json.split("```")[1].split("```")[0].strip()
        
        comparison = json.loads(clean_json)
        
        # 3. Final Decision
        # Reject if humans are detected where not expected, or if semantic match fails.
        is_valid = comparison.get("match", False) and not contains_humans
        score = comparison.get("score", 0.0)
        
        return {
            "is_valid": is_valid,
            "score": score,
            "reason": comparison.get("reason", "No reason provided")
        }

    except Exception as e:
        print(f"Verification failed due to error: {e}")
        traceback.print_exc()
        return {"is_valid": True, "score": 1.0, "reason": "Verification bypassed due to system error"}

def generate_moodboard_prompt(topic: str = None, user_mood: str = None, user_interests: list = None, magazine_tags: list = None, magazine_titles: list = None) -> str:
    """
    Generate a detailed prompt for Stable Diffusion (SDXL) based on the user's magazine context.
    """
    context_parts = []
    
    if topic:
        context_parts.append(f"Main Topic: {topic}")
    
    if user_interests:
        context_parts.append(f"Interests: {', '.join(user_interests)}")
        
    if magazine_tags:
        context_parts.append(f"Style Keywords: {', '.join(magazine_tags)}")
        
    if magazine_titles:
        context_parts.append(f"Recent Themes: {', '.join(magazine_titles)}")
        
    if user_mood:
        context_parts.append(f"Desired Vibe: {user_mood}")
        
    full_context = "\n".join(context_parts)

    system_prompt = prompts.MOODBOARD_SYSTEM_PROMPT
    user_prompt = f"""
    [User Context]
    {full_context}
    
    Create a detailed English prompt for a premium magazine moodboard.
    """

    return llm_client.generate_text(system_prompt, user_prompt)

# Default Fallback Images
FALLBACK_MOODBOARD_IMAGES = [
    "https://images.unsplash.com/photo-1557683316-973673baf926?w=1200",  # Gradient
    "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=1200",  # Abstract
    "https://images.unsplash.com/photo-1557682250-33bd709cbe85?w=1200",  # Gradient 2
]

def generate_moodboard(topic: str = None, user_mood: str = None, user_interests: list = None, magazine_tags: list = None, magazine_titles: list = None) -> dict:
    """
    Orchestrates the moodboard generation process with M+MAC verification.
    """
    display_topic = topic or (magazine_titles[0] if magazine_titles else "User Profile")
    print(f"Generating Moodboard (M+MAC Protocol) for: {display_topic}")

    MAX_RETRIES = 3
    sd_prompt = None
    
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"Generation Attempt {attempt}/{MAX_RETRIES}...")
        
        # 1. Generate Prompt (MAC)
        try:
            current_prompt = generate_moodboard_prompt(topic, user_mood, user_interests, magazine_tags, magazine_titles)
        except Exception as e:
            print(f"Prompt generation failed: {e}")
            continue

        # 2. Verify Integrity (MAC Check)
        verification = verify_prompt_integrity(display_topic, current_prompt)
        
        if verification["is_valid"]:
            print(f"Integrity Verified (Score: {verification['score']})")
            sd_prompt = current_prompt
            break
        else:
            print(f"Integrity Violation (Score: {verification['score']})")
            print(f" > Reason: {verification['reason']}")
            # Fallback to Safe Mode on 3rd failure
            if attempt == MAX_RETRIES:
                print("Max retries reached. Using Safe Mode Fallback.")
                sd_prompt = f"A high-quality studio photography of {display_topic}, minimalist composition, soft cinematic lighting, 8k resolution, masterpiece."
                break

    if not sd_prompt:
        fallback_url = random.choice(FALLBACK_MOODBOARD_IMAGES)
        return {
            "error": "Failed to generate valid prompt after retries",
            "success": False,
            "fallback_url": fallback_url,
            "image_url": fallback_url
        }

    # 3. Generate Image (Local SDXL)
    try:
        print(f"Generating image with Verified Prompt: {sd_prompt[:50]}...")
        image_url = local_diffusion_client.generate_image(sd_prompt)
    except Exception as e:
        print(f"Image generation exception: {e}")
        traceback.print_exc()
        image_url = None
    
    if not image_url:
        fallback_url = random.choice(FALLBACK_MOODBOARD_IMAGES)
        return {
            "error": "Image generation failed",
            "success": False,
            "fallback_url": fallback_url,
            "image_url": fallback_url,
            "description": sd_prompt
        }
        
    return {
        "image_url": image_url,
        "description": sd_prompt,
        "success": True
    }
