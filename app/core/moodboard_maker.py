from app.core.llm_client import llm_client
from app.core.local_diffusion_client import local_diffusion_client
import traceback
import time
import os

NO_HUMAN_NEGATIVE_PROMPT = (
    "no people, no humans, no human, no person, no face, no portrait, no hands, "
    "no arms, no legs, no feet, no body, no mannequin, no model, no silhouette, "
    "person, people, human, face, portrait, hands, arms, legs, feet, body, mannequin, model"
)

NO_TEXT_BRAND_NEGATIVE_PROMPT = (
    "no logos, no text, no labels, no brand marks, no typography, no letters, "
    "no words, no watermark, no signature, no product label close-up, logos, text, labels, "
    "brand marks, typography, letters, words, watermark"
)

BASE_MOODBOARD_NEGATIVE_PROMPT = (
    "nsfw, nude, naked, violence, blood, gore, sexually explicit, weapons, drugs, horror, "
    "disturbing, offensive, inappropriate, pornographic, erotic, suggestive, low quality, blurry, "
    "messy composition, random snapshot, distorted objects, extra limbs, single product shot, "
    "single product photo, product advertisement, catalog photo, isolated object, oversized clothing item"
)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def get_moodboard_generation_config() -> dict:
    return {
        "width": _env_int("MOODBOARD_WIDTH", 768),
        "height": _env_int("MOODBOARD_HEIGHT", 768),
        "steps": _env_int("MOODBOARD_STEPS", 12),
        "guidance_scale": _env_float("MOODBOARD_GUIDANCE_SCALE", 6.0),
        "output_format": os.getenv("MOODBOARD_IMAGE_FORMAT", "JPEG"),
        "quality": _env_int("MOODBOARD_IMAGE_QUALITY", 82),
    }


def build_no_human_negative_prompt() -> str:
    return f"{BASE_MOODBOARD_NEGATIVE_PROMPT}, {NO_HUMAN_NEGATIVE_PROMPT}, {NO_TEXT_BRAND_NEGATIVE_PROMPT}"


def select_visual_elements(topic: str = None, user_interests: list = None, magazine_tags: list = None) -> dict:
    context = " ".join(
        str(part).lower()
        for part in [topic or "", " ".join(user_interests or []), " ".join(magazine_tags or [])]
    )
    categories = [
        (
            "fashion_clothing_sportswear",
            ["fashion", "clothing", "golfwear", "golf wear", "sportswear", "운동복", "골프웨어", "패션", "의류"],
            "folded polo fabric swatch, cropped folded garment details, technical textile texture, stitching detail, golf gloves, golf balls, tee, club head detail, green grass texture, color palette cards, premium textile swatches",
        ),
        (
            "interior_home_furniture",
            ["interior", "home", "furniture", "인테리어", "홈", "가구", "home office", "홈 오피스"],
            "furniture details, textile samples, desk lamp, keyboard, notebook, ergonomic chair detail, plant, wall texture, decor objects, soft lighting",
        ),
        (
            "tech",
            ["tech", "it", "ai", "device", "electronics", "테크", "기술", "전자", "디바이스"],
            "devices, chips, cables, screens, keyboard detail, glass texture, metal texture, clean desk setup",
        ),
        (
            "food",
            ["food", "cafe", "restaurant", "coffee", "음식", "푸드", "카페", "맛집", "요리"],
            "ingredients, plates, utensils, ceramic bowls, table setting, linen texture, steam, natural food textures",
        ),
        (
            "travel",
            ["travel", "trip", "여행", "트래블", "도시", "휴가"],
            "map, luggage detail, tickets, local objects, postcards, landscape-inspired color palette, woven textile, no tourists",
        ),
        (
            "beauty_perfume",
            ["beauty", "perfume", "skincare", "cosmetic", "뷰티", "향수", "화장품", "스킨케어"],
            "perfume bottles, skincare packaging, botanicals, glass, petals, cream texture, reflective tray, soft fabric",
        ),
    ]
    for category, keywords, elements in categories:
        if any(keyword in context for keyword in keywords):
            return {"category": category, "elements": elements}
    return {
        "category": "generic_editorial_object_moodboard",
        "elements": "curated objects, material samples, color swatches, paper textures, decor details, tasteful lighting",
    }


def enforce_no_human_moodboard_prompt(prompt: str, visual_elements: dict) -> str:
    style = (
        "premium editorial moodboard, aesthetic product collage, clean wallpaper composition, "
        "curated object flatlay, cohesive color palette, tasteful lighting, design magazine style, "
        "balanced layout, multiple curated objects, material swatches, color palette cards, "
        "magazine brand board, not a single product shot"
    )
    layout_rule = (
        "5 to 8 related objects and material or color elements arranged with balanced spacing, "
        "no single item dominates the frame, no full shirt as the main subject, "
        "fabric swatches and folded garment details instead of a whole clothing product"
    )
    no_human_rule = (
        "strictly no people, no humans, no person, no face, no portrait, no hands, no arms, "
        "no legs, no feet, no body, no mannequin, no model, no silhouette"
    )
    no_text_rule = "no logos, no text, no labels, no brand marks, no typography"
    return (
        f"{prompt}, {style}, visual elements: {visual_elements['elements']}, "
        f"{layout_rule}, object and material focused, brand board composition, "
        f"{no_human_rule}, {no_text_rule}"
    )

def generate_moodboard_prompt(topic: str = None, user_mood: str = None, user_interests: list = None, magazine_tags: list = None, magazine_titles: list = None, request_id: str = None) -> str:
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
    visual_elements = select_visual_elements(topic, user_interests, magazine_tags)

    system_prompt = f"""
    You are an award-winning Art Director and Senior Photographer.
    Your mission is to craft a HIGH-END, ATMOSPHERIC SDXL prompt for M:ine magazine's moodboard.
    The image must be a people-free object moodboard, not a portrait, not a model shot, not a lifestyle photo with humans.
    
    [LANGUAGE RULE — ABSOLUTE]
    Your output MUST be in ENGLISH ONLY. No Korean, Chinese, Japanese, or any non-Latin characters.
    Even if the topic is in Korean, you MUST translate it to English for the prompt.
    Example: "홈트레이닝" → "home workout", "부산 맛집" → "Busan restaurant"
    
    [SUBJECT-SPECIFIC FOCUS (MANDATORY)]
    The image MUST clearly feature elements of: {topic_emphasis}
    It MUST show object/product/material elements instead of humans.
    Selected visual object palette: {visual_elements['elements']}
    The result must feel like an editorial moodboard or magazine brand board, not a single product photo or advertisement.
    It must show 5 to 8 related objects/material/color elements with balanced spacing.
    Match the topic to the most relevant category and follow its guidance:
    - **Food/Cafe**: Detail-oriented food photography. Focus on textures (steam, moisture, crumbs). Artisan ceramics.
    - **Fashion/Beauty**: High-fashion editorial object board. Focus on fabric swatches, cropped folded garment details, stitching, accessories, packaging, bottles, botanicals, and luxury textures. Never use a wearing model, never make one full clothing item dominate the frame.
    - **Travel/Architecture**: Atmospheric object/location-inspired board. Focus on maps, tickets, luggage details, local objects, lighting, scale, and architectural materials. No tourists.
    - **Art/Design**: Abstract or conceptual visuals. Focus on color harmony, shadow play, and artistic objects.
    - **Tech/Minimal**: Futuristic and clean. Focus on sleek surfaces, light-ray effects, and UI-inspired aesthetics.
    - **Fitness/Health/Sports**: Athletic and energetic object board. Focus on workout equipment, golf balls, club heads, gloves, shoes, fabric, yoga mat, dumbbells, resistance bands, water bottle, gym or home workout objects. No active body movement and no people.
    - **Lifestyle/Wellness**: Serene and balanced. Focus on self-care items (candles, plants, journals), cozy home interior, morning routines, healthy food prep, mindfulness.
    - **Music/Entertainment**: Dynamic and expressive. Focus on instruments, concert lighting, vinyl records, headphones, stage atmospheres.
    
    [CONCRETE OBJECTS REQUIRED]
    You MUST include 5-8 specific physical objects/material/color elements in the prompt that are directly related to the topic.
    - BAD: "fitness concept, healthy lifestyle, motivation" (too abstract)
    - BAD: "model wearing golfwear, athlete portrait, person exercising" (humans are forbidden)
    - BAD: "single polo shirt product photo, centered clothing advertisement, logo label close-up" (too much like a product ad)
    - GOOD: "yoga mat with resistance bands and water bottle, bright home interior" (concrete objects)
    - GOOD: "folded polo fabric swatch, golf glove, golf ball, tee, club head detail, grass texture, color palette cards, stitching detail"
    
    [PHOTOGRAPHY PARAMETERS]
    1. **Subject**: Specific, high-definition product/object/material subjects related to the Topic ({topic_emphasis}). Include real objects.
    2. **Composition**: balanced layout, multiple curated objects, material swatches, color palette cards, magazine brand board, premium editorial moodboard, aesthetic product collage, clean wallpaper composition, curated object flatlay, cohesive color palette, tasteful lighting, design magazine style, not a single product shot.
    3. **Lighting**: Cinematic lighting (Volumetric light, Soft natural dawn light, Dramatic REMBRANDT shadows).
    4. **Camera/Film**: 85mm lens for products, 24mm for landscapes. High-speed film grain (minimal), crisp focus.
    5. **Style**: Premium magazine editorial style (Kinfolk, Magazine B, Vogue quality).
    
    [PROMPT STRUCTURE]
    [Subject Detail with concrete objects], [Environment/Atmosphere], [Composition Style], [Specific Lighting], [Camera Settings], [Quality Tags: photorealistic, premium editorial]
    
    [CRITICAL CONSTRAINTS]
    - **NSFW POLICY**: NEVER generate prompts for pornography, explicit sexual acts, extreme violence, or illegal content.
    - If the topic is inappropriate, your entire response MUST be: "FORBIDDEN_CONTENT"
    - Output ONLY the prompt text in ENGLISH. Nothing else.
    - Do NOT use abstract words only. Include SPECIFIC OBJECTS related to the topic.
    - ABSOLUTELY NO HUMANS: no people, no humans, no person, no face, no portrait, no hands, no arms, no legs, no feet, no body, no mannequin, no model, no silhouette.
    - ABSOLUTELY NO TEXT OR BRANDING: no logos, no text, no labels, no brand marks, no typography.
    - Avoid product advertisement composition. No single product should occupy most of the frame.
    - For fashion, golfwear, sportswear, fitness, and beauty topics, show products, equipment, packaging, fabric, texture, and accessories only.
    - Ensure the mood aligns with: {user_mood or "Sophisticated"}
    """

    user_prompt = f"""
    [User Context]
    {full_context}
    
    Create a comma-separated ENGLISH prompt for a sophisticated people-free editorial moodboard/wallpaper image.
    Remember: ENGLISH ONLY, include 5-8 balanced curated objects/material/color elements related to the topic.
    Do not include people, body parts, logos, text, labels, brand marks, or typography.
    """

    prompt = llm_client.generate_text(system_prompt, user_prompt)
    if prompt and prompt.strip() == "FORBIDDEN_CONTENT":
        return "FORBIDDEN_CONTENT"
    return enforce_no_human_moodboard_prompt(prompt, visual_elements)

# 기본 Fallback 이미지 (SDXL 실패 시 사용) — Unsplash 그라디언트 제거
# 무드보드는 AI 생성이므로, 실패 시 fallback URL 없이 에러 반환
FALLBACK_MOODBOARD_IMAGES = []


def generate_moodboard(topic: str = None, user_mood: str = None, user_interests: list = None, magazine_tags: list = None, magazine_titles: list = None, request_id: str = None) -> dict:
    """
    Orchestrates the moodboard generation process using Stable Diffusion.
    Returns structured response with success indicator and fallback on failure.
    
    Returns:
        On success: {"image_url": "...", "description": "...", "success": True}
        On failure: {"error": "...", "error_type": "...", "success": False, "fallback_url": "..."}
    """
    # 토픽이 없으면 태그나 타이틀로 대체 토픽 설정 (로깅용)
    display_topic = topic or (magazine_titles[0] if magazine_titles else "User Profile")
    visual_elements = select_visual_elements(topic or display_topic, user_interests, magazine_tags)
    generation_config = get_moodboard_generation_config()
    negative_prompt = build_no_human_negative_prompt()
    
    start_time = time.perf_counter()
    timings = {
        "moodboard_style_policy": "no_human_editorial",
        "no_human": True,
        "image_width": generation_config["width"],
        "image_height": generation_config["height"],
        "inference_steps": generation_config["steps"],
        "guidance_scale": generation_config["guidance_scale"],
        "negative_prompt_applied": True,
        "selected_object_palette": visual_elements["category"],
        "selected_visual_elements": visual_elements["elements"],
    }
    log_prefix = f"[moodboard][request_id={request_id}]" if request_id else "[moodboard]"
    print(f"{log_prefix} 🎨 Generating Background Moodboard (SDXL) for: {display_topic}")
    print(
        f"{log_prefix} policy: moodboard_style_policy=no_human_editorial "
        f"no_human=true image_width={generation_config['width']} image_height={generation_config['height']} "
        f"inference_steps={generation_config['steps']} guidance_scale={generation_config['guidance_scale']} "
        f"negative_prompt_applied=true selected_object_palette={visual_elements['category']} "
        f"selected_visual_elements={visual_elements['elements']}"
    )

    # 1. Generate Prompt
    try:
        prompt_start = time.perf_counter()
        sd_prompt = generate_moodboard_prompt(topic, user_mood, user_interests, magazine_tags, magazine_titles, request_id=request_id)
        timings["moodboard_prompt_generation_time"] = round(time.perf_counter() - prompt_start, 3)
        print(f"{log_prefix} ✨ SDXL Prompt: {sd_prompt}")
    except Exception as e:
        timings["moodboard_prompt_generation_time"] = round(time.perf_counter() - start_time, 3)
        print(f"{log_prefix} ❌ Prompt generation failed: {e}")
        sd_prompt = None

    if not sd_prompt or sd_prompt.strip() == "FORBIDDEN_CONTENT":
        return {
            "error": "Forbidden content detected or prompt generation failed",
            "error_type": "FORBIDDEN_CONTENT" if sd_prompt == "FORBIDDEN_CONTENT" else "PROMPT_GENERATION_FAILED",
            "success": False,
            "status": "FAILED",
            "fallback_url": None,
            "image_url": None,
            "description": f"Safety filter blocked prompt generation for: {display_topic}",
            "timing": {**timings, "moodboard_generation_time": round(time.perf_counter() - start_time, 3)}
        }

    # 2. Generate Image (Local SDXL)
    try:
        print(f"{log_prefix} 🖼️ Generating image with SDXL...")
        image_start = time.perf_counter()
        image_url = local_diffusion_client.generate_image(
            sd_prompt,
            width=generation_config["width"],
            height=generation_config["height"],
            num_inference_steps=generation_config["steps"],
            guidance_scale=generation_config["guidance_scale"],
            negative_prompt=negative_prompt,
            output_format=generation_config["output_format"],
            quality=generation_config["quality"],
        )
        timings["moodboard_image_generation_time"] = round(time.perf_counter() - image_start, 3)
        timings.update({
            f"diffusion_{key}": value
            for key, value in getattr(local_diffusion_client, "last_timing", {}).items()
        })
    except Exception as e:
        timings["moodboard_image_generation_time"] = round(time.perf_counter() - start_time, 3)
        print(f"{log_prefix} ❌ Image generation exception: {e}")
        traceback.print_exc()
        image_url = None
    
    if not image_url:
        return {
            "error": "Failed to generate image - SDXL model may not be loaded",
            "error_type": "IMAGE_GENERATION_FAILED",
            "success": False,
            "status": "FAILED",
            "fallback_url": None,
            "image_url": None,
            "description": sd_prompt,
            "timing": {**timings, "moodboard_generation_time": round(time.perf_counter() - start_time, 3)}
        }
        
    timings["moodboard_generation_time"] = round(time.perf_counter() - start_time, 3)
    print(f"{log_prefix} ✅ Moodboard Generated (Data URI)")
    print(f"{log_prefix} timing: {timings}")

    return {
        "image_url": image_url,  # This will be a Data URI (base64)
        "description": sd_prompt,
        "success": True,
        "status": "COMPLETED",
        "timing": timings
    }
