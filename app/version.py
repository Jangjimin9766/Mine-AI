import os


def _magazine_contract_info() -> dict:
    try:
        from app.core.magazine_maker import PARAGRAPH_MAX_CHARS, PARAGRAPH_MIN_CHARS

        return {
            "paragraph_min_chars": PARAGRAPH_MIN_CHARS,
            "paragraph_max_chars": PARAGRAPH_MAX_CHARS,
            "paragraph_length_policy": f"{PARAGRAPH_MIN_CHARS}-{PARAGRAPH_MAX_CHARS}",
        }
    except Exception as exc:
        return {
            "paragraph_min_chars": "unknown",
            "paragraph_max_chars": "unknown",
            "paragraph_length_policy": "unknown",
            "paragraph_contract_error": exc.__class__.__name__,
        }


def get_runtime_info() -> dict:
    commit = (
        os.getenv("GIT_COMMIT")
        or os.getenv("APP_VERSION")
        or os.getenv("RUNPOD_IMAGE_TAG")
        or "unknown"
    )
    return {
        "version": commit[:12] if commit != "unknown" else commit,
        "git_commit": commit,
        **_magazine_contract_info(),
        "magazine_shape": "2x3",
        "sections_per_magazine": 2,
        "paragraphs_per_section": 3,
        "moodboard_in_create": True,
        "moodboard_generation": "included_in_create_magazine",
        "timing_logging_enabled": True,
        "moodboard_required_in_create": True,
        "sdxl_inference_steps_default": int(os.getenv("SDXL_INFERENCE_STEPS", "14")),
        "moodboard_width": int(os.getenv("MOODBOARD_WIDTH", "768")),
        "moodboard_height": int(os.getenv("MOODBOARD_HEIGHT", "768")),
        "moodboard_steps": int(os.getenv("MOODBOARD_STEPS", "12")),
        "moodboard_guidance_scale": float(os.getenv("MOODBOARD_GUIDANCE_SCALE", "6.0")),
        "moodboard_image_quality": int(os.getenv("MOODBOARD_IMAGE_QUALITY", "88")),
        "moodboard_style_policy": "no_human_editorial",
        "optimization_profile": "timed_create_magazine_fast_sdxl",
        "spring_internal_callback_in_create_magazine": False,
        "spring_internal_callback_action": "spring_internal_callback",
        "jina_read_timeout_seconds": float(os.getenv("JINA_READ_TIMEOUT_SECONDS", "3")),
        "jina_scrape_budget_seconds": float(os.getenv("JINA_SCRAPE_BUDGET_SECONDS", "8")),
        "jina_max_urls": int(os.getenv("JINA_MAX_URLS", "3")),
        "image_validation_timeout_seconds": float(os.getenv("IMAGE_VALIDATION_TIMEOUT_SECONDS", "1")),
    }
