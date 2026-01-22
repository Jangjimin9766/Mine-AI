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
    You are an award-winning Art Director and Senior Photographer.
    Your mission is to craft a HIGH-END, ATMOSPHERIC SDXL prompt for M:ine magazine's moodboard.
    
    [SUBJECT-SPECIFIC FOCUS (MANDATORY)]
    The image MUST clearly feature elements of: {topic_emphasis}
    - **Food/Cafe**: Detail-oriented food photography. Focus on textures (steam, moisture, crumbs). Artisan ceramics.
    - **Fashion/Beauty**: High-fashion editorial look. Focus on fabric textures (silk, wool, leather) and luxury accessories.
    - **Travel/Architecture**: Atmospheric location shots. Focus on lighting, scale, and unique architectural details.
    - **Art/Design**: Abstract or conceptual visuals. Focus on color harmony, shadow play, and artistic objects.
    - **Tech/Minimal**: Futuristic and clean. Focus on sleek surfaces, light-ray effects, and UI-inspired aesthetics.
    
    [PHOTOGRAPHY PARAMETERS]
    1. **Subject**: Specific, high-definition subject related to the Topic ({topic_emphasis}).
    2. **Composition**: Choose most effective (Flatlay, Extreme Close-up, Wide landscape, Golden ratio).
    3. **Lighting**: Cinematic lighting (Volumetric light, Soft natural dawn light, Dramatic REMBRANDT shadows).
    4. **Camera/Film**: 85mm lens for products, 24mm for landscapes. High-speed film grain (minimal), crisp focus.
    5. **Style**: Premium magazine editorial style (Kinfolk, Magazine B, Vogue quality).
    
    [PROMPT STRUCTURE]
    [Subject Detail], [Environment/Atmosphere], [Composition Style], [Specific Lighting], [Camera Settings], [Quality Tags: 8k, photorealistic, mastery, masterpiece]
    
    [CRITICAL CONSTRAINTS]
    - Output ONLY the prompt text.
    - Do NOT use abstract words only. The Topic MUST be the hero of the image.
    - Ensure the mood aligns with: {user_mood or "Sophisticated"}
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
