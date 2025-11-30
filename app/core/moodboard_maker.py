from app.core.llm_client import llm_client
from app.core.local_diffusion_client import local_diffusion_client

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

    system_prompt = f"""
    You are an expert Art Director specializing in UI/UX and Interior Design.
    Your task is to create a prompt for a 'Background Moodboard' image (Wallpaper) for Stable Diffusion XL.
    
    [DESIGN GOALS]
    1. **Role**: This image will be used as a BACKGROUND for a user profile or app interface.
    2. **Aesthetic**: Atmospheric, textural, abstract, or scenic. NOT cluttered.
    3. **Vibe**: Sophisticated, premium, 'Kinfolk' or 'Architectural Digest' style.
    4. **Variation**: {random_variation}
    
    [PROMPT FORMAT]
    - Stable Diffusion works best with comma-separated keywords.
    - Start with the main subject/vibe.
    - Add style modifiers (e.g., "cinematic lighting", "8k", "unreal engine", "minimalist").
    - Add negative prompt keywords implicitly by focusing on what TO include (clean, open space).
    
    Output ONLY the English prompt.
    Example: "abstract geometric shapes, soft pastel colors, minimalist, high quality, 8k, cinematic lighting, wallpaper, texture"
    """

    user_prompt = f"""
    [User Context]
    {full_context}
    
    Create a comma-separated prompt for a sophisticated BACKGROUND image.
    """

    return llm_client.generate_text(system_prompt, user_prompt)

def generate_moodboard(topic: str = None, user_mood: str = None, user_interests: list = None, magazine_tags: list = None, magazine_titles: list = None) -> dict:
    """
    Orchestrates the moodboard generation process using Stable Diffusion.
    """
    # 토픽이 없으면 태그나 타이틀로 대체 토픽 설정 (로깅용)
    display_topic = topic or (magazine_titles[0] if magazine_titles else "User Profile")
    
    print(f"🎨 Generating Background Moodboard (SDXL) for: {display_topic}")

    # 1. Generate Prompt
    sd_prompt = generate_moodboard_prompt(topic, user_mood, user_interests, magazine_tags, magazine_titles)
    print(f"✨ SDXL Prompt: {sd_prompt}")

    if not sd_prompt:
        return None

    # 2. Generate Image (Local SDXL)
    image_url = local_diffusion_client.generate_image(sd_prompt)
    
    if not image_url:
        return None
        
    print(f"✅ Moodboard Generated (Data URI)")

    return {
        "image_url": image_url, # This will be a Data URI (base64)
        "description": sd_prompt
    }
