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
        "moodboard_in_create": False,
        "moodboard_generation": "separate_generate_moodboard_action",
    }
