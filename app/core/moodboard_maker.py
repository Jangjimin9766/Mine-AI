from app.core.llm_client import llm_client

def generate_moodboard_prompt(topic: str = None, user_mood: str = None, user_interests: list = None, magazine_tags: list = None, magazine_titles: list = None) -> str:
    """
    Generate a detailed prompt for DALL-E 3 based on the user's magazine context.
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
    Your task is to create a prompt for a 'Background Moodboard' image (Wallpaper).
    
    [DESIGN GOALS]
    1. **Role**: This image will be used as a BACKGROUND for a user profile or app interface.
    2. **Aesthetic**: Atmospheric, textural, abstract, or scenic. NOT cluttered.
    3. **Composition**: Open space, soft focus, or pattern-based. Avoid central focal points that fight with foreground text.
    4. **Vibe**: Sophisticated, premium, 'Kinfolk' or 'Architectural Digest' style.
    5. **Content**: Abstract representations of the user's interests/themes.
    6. **Variation**: {random_variation}
    
    [RESTRICTIONS]
    - NO TEXT in the image.
    - NO human faces (silhouettes or distant figures are okay).
    - NO complex scenes that look like a photo snapshot.
    
    Output ONLY the English prompt for DALL-E 3.
    """

    user_prompt = f"""
    [User Context]
    {full_context}
    
    Create a prompt for a sophisticated BACKGROUND image that captures this essence.
    """

    return llm_client.generate_text(system_prompt, user_prompt)

def generate_moodboard(topic: str = None, user_mood: str = None, user_interests: list = None, magazine_tags: list = None, magazine_titles: list = None) -> dict:
    """
    Orchestrates the moodboard generation process.
    """
    # 토픽이 없으면 태그나 타이틀로 대체 토픽 설정 (로깅용)
    display_topic = topic or (magazine_titles[0] if magazine_titles else "User Profile")
    
    print(f"🎨 Generating Background Moodboard for: {display_topic}")

    # 1. Generate Prompt
    dalle_prompt = generate_moodboard_prompt(topic, user_mood, user_interests, magazine_tags, magazine_titles)
    print(f"✨ DALL-E Prompt: {dalle_prompt}")

    if not dalle_prompt:
        return None

    # 2. Generate Image
    image_url = llm_client.generate_image(dalle_prompt)
    
    if not image_url:
        return None
        
    print(f"✅ Moodboard Generated: {image_url}")

    return {
        "image_url": image_url,
        "description": dalle_prompt
    }
