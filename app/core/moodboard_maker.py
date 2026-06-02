from app.core.llm_client import llm_client
from app.core.local_diffusion_client import local_diffusion_client
import traceback
import time
import os
import re

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
    "single product photo, product advertisement, catalog photo, isolated object, oversized clothing item, "
    "flat boring layout, paper grid layout, scrapbook layout, empty composition, dull lighting, "
    "washed out colors, generic stock photo"
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
        "quality": _env_int("MOODBOARD_IMAGE_QUALITY", 88),
    }


def build_no_human_negative_prompt() -> str:
    return f"{BASE_MOODBOARD_NEGATIVE_PROMPT}, {NO_HUMAN_NEGATIVE_PROMPT}, {NO_TEXT_BRAND_NEGATIVE_PROMPT}"


WEAK_MOODBOARD_KEYWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "is", "it", "its", "my", "of", "on", "or", "the", "this", "to",
    "what", "with", "posted", "posted oct", "posted nov", "login", "naver",
    "blog", "로그인", "네이버", "블로그", "본문", "댓글", "공유", "검색",
    "지면보기", "구독", "회원가입",
}


def _source_keyword_phrases(values: list, max_items: int = 6) -> list:
    phrases = []
    seen = set()
    for value in values or []:
        text = str(value or "").strip()
        if not text:
            continue
        text = re.sub(r"https?://\S+", " ", text)
        text = re.sub(r"[^\w\s가-힣&'-]", " ", text)
        candidates = re.findall(
            r"[A-Za-z][A-Za-z0-9&' -]{1,40}|[가-힣][가-힣A-Za-z0-9\s]{1,40}",
            text,
        )
        for candidate in candidates:
            normalized = " ".join(candidate.lower().split())
            if (
                normalized
                and normalized not in WEAK_MOODBOARD_KEYWORDS
                and not normalized.startswith("posted ")
                and not any(term in normalized for term in ("로그인", "지면보기", "구독", "댓글"))
                and normalized not in seen
            ):
                seen.add(normalized)
                phrases.append(" ".join(candidate.split()))
            if len(phrases) >= max_items:
                return phrases
    return phrases


TOPIC_OBJECT_ANCHORS = [
    (
        ("텀블러", "tumbler", "reusable cup", "reusable bottle"),
        [
            "stainless steel reusable tumbler",
            "bamboo bottle cleaning brush",
            "silicone straw case",
            "microfiber drying cloth",
            "cork coaster",
            "clear refill bottle",
        ],
    ),
    (
        ("홈트", "workout", "exercise", "fitness"),
        [
            "yoga mat",
            "hex dumbbells",
            "resistance bands",
            "foam roller",
            "water bottle",
            "workout timer",
        ],
    ),
    (
        ("인테리어", "interior", "작은 집", "small home", "space saving"),
        [
            "modular storage cubes",
            "round wall mirror",
            "floating oak shelf",
            "linen fabric swatches",
            "light oak flooring sample",
            "neutral color cards",
        ],
    ),
    (
        ("요리", "레시피", "food", "recipe", "cooking"),
        [
            "ceramic serving bowl",
            "wooden spoon",
            "ingredient bowls",
            "linen napkin",
            "stone countertop sample",
            "warm color cards",
        ],
    ),
]


def _topic_object_anchors(values: list, max_items: int = 6) -> list:
    haystack = " ".join(str(value or "").lower() for value in values or [])
    anchors = []
    seen = set()
    for triggers, objects in TOPIC_OBJECT_ANCHORS:
        if any(trigger.lower() in haystack for trigger in triggers):
            for obj in objects:
                if obj not in seen:
                    seen.add(obj)
                    anchors.append(obj)
                if len(anchors) >= max_items:
                    return anchors
    return anchors


def _clean_prompt_phrase(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\[[^\]]+\]", " ", text)
    text = re.sub(r"[^A-Za-z0-9&' -]", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" ,.-")
    return text


def _prompt_object_phrases(prompt: str, max_items: int = 5) -> list:
    phrases = []
    seen = set()
    for raw_part in re.split(r"[,;]", str(prompt or "")):
        phrase = _clean_prompt_phrase(raw_part)
        normalized = phrase.lower()
        if (
            not phrase
            or len(phrase) < 3
            or len(phrase) > 48
            or normalized in seen
            or any(term in normalized for term in (
                "premium", "editorial", "moodboard", "photorealistic", "cinematic",
                "camera", "quality", "negative space", "composition",
                "no people", "no human", "no text", "no logo",
            ))
        ):
            continue
        seen.add(normalized)
        phrases.append(phrase)
        if len(phrases) >= max_items:
            break
    return phrases


def _compact_sdxl_prompt(prompt: str, visual_elements: dict) -> str:
    anchors = visual_elements.get("object_anchors") or []
    llm_objects = _prompt_object_phrases(prompt)
    objects = []
    seen = set()
    for item in [*anchors, *llm_objects]:
        phrase = _clean_prompt_phrase(item)
        normalized = phrase.lower()
        if phrase and normalized not in seen:
            seen.add(normalized)
            objects.append(phrase)
        if len(objects) >= 5:
            break

    object_text = ", ".join(objects) if objects else _clean_prompt_phrase(prompt)[:220]
    source_keyword_items = []
    for keyword in visual_elements.get("keywords", [])[:4]:
        cleaned = _clean_prompt_phrase(keyword)
        if cleaned and re.search(r"[A-Za-z]{3,}", cleaned):
            source_keyword_items.append(cleaned)
    source_keywords = ", ".join(source_keyword_items)
    source_rule = f"source constraint: {source_keywords}" if source_keywords else "source constraint: topic objects"
    return (
        f"{object_text}, premium editorial cover background, layered still-life composition, magazine brand board, "
        "one clear hero object with supporting material layers, color palette cards, tactile details, "
        "balanced asymmetrical composition, refined negative space for app title overlay, subtle shadows, "
        "cinematic depth cues, soft directional daylight, cohesive color story, crisp texture, "
        "high-end design magazine styling, photorealistic, "
        f"no people, no humans, no hands, no model, no text, no logos, no single product shot, "
        f"not a single product shot, no paper flatlay grid, {source_rule}"
    )


def select_visual_elements(
    topic: str = None,
    user_interests: list = None,
    magazine_tags: list = None,
    magazine_titles: list = None,
    section_headings: list = None,
    content_keywords: list = None,
) -> dict:
    if topic:
        source_values = [topic or "", *(section_headings or []), *(content_keywords or []), *(magazine_tags or []), *(magazine_titles or [])]
    else:
        source_values = [*(section_headings or []), *(content_keywords or []), *(user_interests or []), *(magazine_tags or []), *(magazine_titles or [])]
    keyword_phrases = _source_keyword_phrases(source_values)
    object_anchors = _topic_object_anchors(source_values)
    if keyword_phrases:
        elements = (
            "translate if needed and use only visual subjects derived from these supplied magazine keywords: "
            + ", ".join(keyword_phrases)
        )
    else:
        elements = (
            "use only concrete objects, materials, colors, locations, and visual details "
            "explicitly implied by the translated topic and supplied magazine context"
        )
    return {
        "category": "keyword_driven",
        "elements": elements,
        "keywords": keyword_phrases,
        "object_anchors": object_anchors,
    }


def enforce_no_human_moodboard_prompt(prompt: str, visual_elements: dict) -> str:
    return _compact_sdxl_prompt(prompt, visual_elements)


def generate_moodboard_prompt(topic: str = None, user_mood: str = None, user_interests: list = None, magazine_tags: list = None, magazine_titles: list = None, section_headings: list = None, content_keywords: list = None, request_id: str = None) -> str:
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

    if section_headings:
        context_parts.append(f"Magazine Section Headings: {', '.join(section_headings)}")

    if content_keywords:
        context_parts.append(f"Article Content Keywords: {', '.join(content_keywords)}")
        
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
    if section_headings:
        topic_keywords.extend(section_headings)
    if content_keywords:
        topic_keywords.extend(content_keywords)
    
    topic_emphasis = ", ".join(topic_keywords) if topic_keywords else "general lifestyle"
    visual_elements = select_visual_elements(topic, user_interests, magazine_tags, magazine_titles, section_headings, content_keywords)
    object_anchors = visual_elements.get("object_anchors") or []
    object_anchor_text = ", ".join(object_anchors) if object_anchors else "objects explicitly named or directly implied by the supplied magazine keywords"

    system_prompt = f"""
    You are an award-winning Art Director and Senior Photographer.
    Your mission is to craft a HIGH-END, ATMOSPHERIC SDXL prompt for M:ine magazine's cover moodboard.
    The image must be a people-free editorial cover background, not a portrait, not a model shot, not a lifestyle photo with humans.

    [LANGUAGE RULE — ABSOLUTE]
    Your output MUST be in ENGLISH ONLY. No Korean, Chinese, Japanese, or any non-Latin characters.
    Even if the topic is in Korean, you MUST translate it to English for the prompt.
    Example: "홈트레이닝" → "home workout", "부산 맛집" → "Busan restaurant"

    [SUBJECT-SPECIFIC FOCUS — MANDATORY]
    The image MUST clearly feature elements of: {topic_emphasis}
    It MUST visibly include these primary anchor objects when applicable: {object_anchor_text}
    It MUST show object, product, material, and color elements instead of humans.
    Source keywords and constraints: {visual_elements['elements']}
    Magazine section headings and article content keywords are stronger than generic title, tag, or user mood signals.
    The result must feel like a premium editorial cover background or magazine brand board, not a single product photo or advertisement.
    Use a hero object plus supporting layers: 1 clear focal object, 1-2 secondary objects, 2-3 material or texture layers, and 2 color palette accents.
    Use a wide editorial still-life composition with clean negative space so it works as an app cover background.
    Do not use a paper grid, scrapbook layout, macro close-up, cropped close-up, or one oversized object filling the frame.
    Do not use a fixed category palette. Derive every object from the supplied topic, titles, tags, and source keywords.

    [CONCRETE OBJECTS REQUIRED]
    You MUST include a specific hero object and supporting physical objects, materials, textures, or color accents directly related to the supplied topic and magazine keywords.
    Use the primary anchor objects as the first visual subjects in the prompt; do not replace them with generic category props.
    - BAD: "premium concept, lifestyle, motivation" (too abstract)
    - BAD: "model wearing clothes, athlete portrait, person using product" (humans are forbidden)
    - BAD: "single centered product photo, advertisement, logo close-up" (too much like a product ad)
    - GOOD: a clear hero object, secondary objects, material textures, color palette accents, surfaces, and props directly implied by the supplied magazine keywords.

    [PHOTOGRAPHY PARAMETERS]
    1. Subject: specific, high-definition product/object/material subjects related to the Topic ({topic_emphasis}) and source keywords.
    2. Composition: premium editorial cover background, layered still-life composition, one clear hero object with supporting material layers, color palette accents, magazine brand board, clean wallpaper composition, cohesive color story, refined negative space for app title overlay, tasteful lighting, design magazine style, not a single product shot, not a paper flatlay grid.
    3. Lighting: cinematic volumetric light, soft natural dawn light, dramatic Rembrandt shadows.
    4. Camera/Film: 85mm lens for products, f/5.6, ISO 100, crisp focus, minimal grain.
    5. Style: premium magazine editorial style, Kinfolk, Magazine B, Vogue quality, photorealistic.
    6. Variation: {random_variation}

    [PROMPT STRUCTURE]
    [Hero object and supporting concrete subjects], [Material/Color Story], [Editorial Cover Composition], [Specific Lighting], [Camera Settings], [Quality Tags: photorealistic, premium editorial]

    [CRITICAL CONSTRAINTS]
    - NSFW POLICY: NEVER generate prompts for pornography, explicit sexual acts, extreme violence, or illegal content.
    - If the topic is inappropriate, your entire response MUST be: "FORBIDDEN_CONTENT"
    - Output ONLY the prompt text in ENGLISH. Nothing else.
    - Do NOT use abstract words only. Include SPECIFIC OBJECTS related to the topic.
    - ABSOLUTELY NO HUMANS: no people, no humans, no person, no face, no portrait, no hands, no arms, no legs, no feet, no body, no mannequin, no model, no silhouette.
    - ABSOLUTELY NO TEXT OR BRANDING: no logos, no text, no labels, no brand marks, no typography, no watermarks.
    - Avoid product advertisement composition. No single product should occupy most of the frame.
    - Do not introduce sports equipment, food, travel props, beauty products, devices, or fashion items unless they are present in or directly implied by the supplied keywords.
    - Ensure the mood aligns with: {user_mood or "Sophisticated"}
    """

    user_prompt = f"""
    [User Context]
    {full_context}
    
    Create a comma-separated ENGLISH prompt for a sophisticated people-free editorial cover moodboard image.
    Remember: ENGLISH ONLY, use a hero object plus supporting material layers, texture details, and color accents related to the topic.
    Do not include people, body parts, logos, text, labels, brand marks, or typography.
    """

    prompt = llm_client.generate_text(system_prompt, user_prompt)
    if prompt and prompt.strip() == "FORBIDDEN_CONTENT":
        return "FORBIDDEN_CONTENT"
    enforced_prompt = enforce_no_human_moodboard_prompt(prompt, visual_elements)
    return enforced_prompt

# 기본 Fallback 이미지 (SDXL 실패 시 사용) — Unsplash 그라디언트 제거
# 무드보드는 AI 생성이므로, 실패 시 fallback URL 없이 에러 반환
FALLBACK_MOODBOARD_IMAGES = []


def generate_moodboard(topic: str = None, user_mood: str = None, user_interests: list = None, magazine_tags: list = None, magazine_titles: list = None, section_headings: list = None, content_keywords: list = None, request_id: str = None) -> dict:
    """
    Orchestrates the moodboard generation process using Stable Diffusion.
    Returns structured response with success indicator. Failures do not expose a usable fallback image.
    
    Returns:
        On success: {"image_url": "...", "description": "...", "success": True}
        On failure: {"error": "...", "error_type": "...", "success": False, "fallback_url": None, "image_url": None}
    """
    # 토픽이 없으면 태그나 타이틀로 대체 토픽 설정 (로깅용)
    display_topic = topic or (magazine_titles[0] if magazine_titles else "User Profile")
    visual_elements = select_visual_elements(topic or display_topic, user_interests, magazine_tags, magazine_titles, section_headings, content_keywords)
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
        sd_prompt = generate_moodboard_prompt(topic, user_mood, user_interests, magazine_tags, magazine_titles, section_headings, content_keywords, request_id=request_id)
        timings["moodboard_prompt_generation_time"] = round(time.perf_counter() - prompt_start, 3)
        print(f"{log_prefix} ✨ SDXL Prompt: {sd_prompt}")
    except Exception as e:
        timings["moodboard_prompt_generation_time"] = round(time.perf_counter() - start_time, 3)
        print(f"{log_prefix} ❌ Prompt generation failed: {e}")
        sd_prompt = None

    if not sd_prompt or sd_prompt.strip() in ("FORBIDDEN_CONTENT", "IRRELEVANT_PROMPT"):
        error_type = "FORBIDDEN_CONTENT" if sd_prompt == "FORBIDDEN_CONTENT" else "PROMPT_RELEVANCE_FAILED"
        return {
            "error": "Forbidden content detected or prompt generation failed",
            "error_type": error_type if sd_prompt else "PROMPT_GENERATION_FAILED",
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
