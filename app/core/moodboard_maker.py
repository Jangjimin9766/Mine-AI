from app.core.llm_client import llm_client
from app.core.local_diffusion_client import local_diffusion_client
import traceback

def generate_moodboard_prompt(topic: str = None, user_mood: str = None, user_interests: list = None, magazine_tags: list = None, magazine_titles: list = None) -> str:
    """
    Generate a detailed prompt for Stable Diffusion (SDXL) based on the user's magazine context.
    Focus on creating an atmospheric BACKGROUND/WALLPAPER.
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

    import random
    
    # 다양성을 위한 랜덤 요소 추가
    variations = [
        "Focus on texture and material details.",
        "Use a unique perspective or composition.",
        "Experiment with lighting and shadow play.",
        "Create a more abstract interpretation.",
        "Emphasize color harmony and atmosphere."
    ]
    random_variation = random.choice(variations)

    # 태그에서 실제 주제 키워드 추출 (스타일보다 주제 우선)
    topic_keywords = []
    if topic:
        topic_keywords.append(topic)
    if magazine_tags:
        topic_keywords.extend(magazine_tags)
    
    topic_emphasis = ", ".join(topic_keywords) if topic_keywords else "general lifestyle"

    system_prompt = f"""
    You are an expert Art Director creating prompts for Stable Diffusion XL.
    Your task is to create a 'Background Moodboard' image prompt.
    
    [CRITICAL - MUST INCLUDE THESE TOPICS]
    The image MUST visually represent: {topic_emphasis}
    - If the topic is about food/cookies/cafe → include food photography elements
    - If the topic is about fashion → include fashion/clothing elements  
    - If the topic is about travel/places → include location-specific elements
    - DO NOT ignore the actual topic and only add abstract style words!
    
    [DESIGN GOALS]
    1. **Role**: Background for app interface, but MUST reflect the topic visually.
    2. **Aesthetic**: Clean, atmospheric, professional product/lifestyle photography style.
    3. **Variation**: {random_variation}
    
    [PROMPT FORMAT]
    - Start with the ACTUAL SUBJECT (cookies, food, cafe, fashion item, etc.)
    - Then add photography style (food photography, flatlay, product shot, etc.)
    - Then add lighting/quality modifiers (soft lighting, 8k, professional)
    
    Output ONLY the English prompt.
    Example for cookies/cafe: "gourmet chewy cookies on marble surface, warm cafe aesthetic, food photography, soft natural lighting, cozy atmosphere, 8k, professional"
    Example for fashion: "luxury handbag flatlay, fashion editorial, minimalist, soft shadows, high-end product photography, 8k"
    """

    user_prompt = f"""
    [User Context]
    {full_context}
    
    Create a comma-separated prompt for a sophisticated BACKGROUND image.
    """

    return llm_client.generate_text(system_prompt, user_prompt)

# 기본 Fallback 이미지 (SDXL 실패 시 사용)
FALLBACK_MOODBOARD_IMAGES = [
    "https://images.unsplash.com/photo-1557683316-973673baf926?w=1200",  # Gradient
    "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=1200",  # Abstract
    "https://images.unsplash.com/photo-1557682250-33bd709cbe85?w=1200",  # Gradient 2
]


def generate_moodboard(topic: str = None, user_mood: str = None, user_interests: list = None, magazine_tags: list = None, magazine_titles: list = None) -> dict:
    """
    Orchestrates the moodboard generation process using Stable Diffusion.
    Returns structured response with success indicator and fallback on failure.
    
    Returns:
        On success: {"image_url": "...", "description": "...", "success": True}
        On failure: {"error": "...", "error_type": "...", "success": False, "fallback_url": "..."}
    """
    import random
    
    # 토픽이 없으면 태그나 타이틀로 대체 토픽 설정 (로깅용)
    display_topic = topic or (magazine_titles[0] if magazine_titles else "User Profile")
    
    print(f"🎨 Generating Background Moodboard (SDXL) for: {display_topic}")

    # 1. Generate Prompt
    try:
        sd_prompt = generate_moodboard_prompt(topic, user_mood, user_interests, magazine_tags, magazine_titles)
        print(f"✨ SDXL Prompt: {sd_prompt}")
    except Exception as e:
        print(f"❌ Prompt generation failed: {e}")
        sd_prompt = None

    if not sd_prompt:
        fallback_url = random.choice(FALLBACK_MOODBOARD_IMAGES)
        return {
            "error": "Failed to generate prompt - LLM may not be configured",
            "error_type": "PROMPT_GENERATION_FAILED",
            "success": False,
            "fallback_url": fallback_url,
            # 호환성을 위해 image_url도 fallback으로 제공
            "image_url": fallback_url,
            "description": f"Fallback image for: {display_topic}"
        }

    # 2. Generate Image (Local SDXL)
    try:
        image_url = local_diffusion_client.generate_image(sd_prompt)
    except Exception as e:
        print(f"❌ Image generation exception: {e}")
        traceback.print_exc()
        image_url = None
    
    if not image_url:
        fallback_url = random.choice(FALLBACK_MOODBOARD_IMAGES)
        return {
            "error": "Failed to generate image - SDXL model may not be loaded",
            "error_type": "IMAGE_GENERATION_FAILED",
            "success": False,
            "fallback_url": fallback_url,
            # 호환성을 위해 image_url도 fallback으로 제공
            "image_url": fallback_url,
            "description": sd_prompt
        }
        
    print(f"✅ Moodboard Generated (Data URI)")

    return {
        "image_url": image_url,  # This will be a Data URI (base64)
        "description": sd_prompt,
        "success": True
    }
