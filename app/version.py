import os


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
        "magazine_shape": "2x3",
        "sections_per_magazine": 2,
        "paragraphs_per_section": 3,
        "moodboard_in_create": True,
        "moodboard_generation": "included_in_create_magazine",
        "timing_logging_enabled": True,
        "moodboard_required_in_create": True,
        "sdxl_inference_steps_default": int(os.getenv("SDXL_INFERENCE_STEPS", "20")),
        "optimization_profile": "timed_create_magazine_fast_sdxl",
    }
