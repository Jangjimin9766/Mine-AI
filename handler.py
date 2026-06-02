"""
RunPod Serverless Handler for M:ine AI Server
Converts FastAPI endpoints to RunPod serverless format.
# Rebuild trigger: 2026-01-15-v1 - Added Logtail logging
"""
import runpod
import os
import json
import traceback
import sys
import time
import uuid

# 로깅 설정 (Logtail + 콘솔)
from app.core.logging_config import get_logger
logger = get_logger("runpod-handler")

logger.info("=" * 50)
logger.info("🔧 handler.py is loading...")
logger.info("=" * 50)

logger.info(f"✅ Basic imports done. Python: {sys.version}")
logger.info(f"✅ Working directory: {os.getcwd()}")

try:
    from app.version import get_runtime_info
    runtime_info = get_runtime_info()
    logger.info(
        "🚀 Runtime info: "
        f"git_commit={runtime_info.get('git_commit')} "
        f"paragraph_min_chars={runtime_info.get('paragraph_min_chars')} "
        f"paragraph_max_chars={runtime_info.get('paragraph_max_chars')} "
        f"paragraph_length_policy={runtime_info.get('paragraph_length_policy')}"
    )
except Exception as e:
    logger.error(f"❌ Runtime info load failed: {e}")
    logger.error(traceback.format_exc())

# Test critical imports BEFORE handler runs
try:
    logger.info("📦 Testing app.core imports...")
    from app.core.llm_client import llm_client
    logger.info("✅ llm_client imported")
except Exception as e:
    logger.error(f"❌ llm_client import failed: {e}")
    logger.error(traceback.format_exc())

try:
    logger.info("📦 Testing local_diffusion_client import...")
    from app.core.local_diffusion_client import local_diffusion_client
    logger.info("✅ local_diffusion_client imported")
except Exception as e:
    logger.error(f"❌ local_diffusion_client import failed: {e}")
    logger.error(traceback.format_exc())

logger.info("=" * 50)
logger.info("🎯 All imports completed, defining handler...")
logger.info("=" * 50)

# Ensure environment variables are set for API clients
# These will be passed via RunPod's environment configuration


GENERATION_ACTIONS = {
    "create_magazine",
    "create_moodboard",
    "generate_moodboard",
    "edit_magazine",
    "chat",
    "edit_section",
    "generate_paragraph",
}


def generation_disabled() -> bool:
    return os.getenv("GENERATION_DISABLED", "true").lower() not in ("0", "false", "no", "off")


def _sanitize_callback_payload(value):
    """
    Remove inline base64 images before optional Spring callback.
    Spring's normal create flow receives the full RunPod response directly;
    this callback is only a legacy/optional path and must stay lightweight.
    """
    had_base64 = False

    def sanitize(item):
        nonlocal had_base64
        if isinstance(item, str):
            if item.startswith("data:image/") and "base64," in item[:64]:
                had_base64 = True
                return ""
            return item
        if isinstance(item, list):
            return [sanitize(child) for child in item]
        if isinstance(item, dict):
            return {key: sanitize(child) for key, child in item.items()}
        return item

    return sanitize(value), had_base64


def handler(event):
    """
    Main handler for RunPod Serverless.
    
    Expected input format:
    {
        "input": {
            "action": "create_magazine" | "create_moodboard",
            "data": { ... request payload ... }
        }
    }
    """
    try:
        input_data = event.get("input", {})
        action = input_data.get("action")
        data = input_data.get("data", {})
        
        logger.info(f"🚀 RunPod Handler received action: {action}")

        if action in GENERATION_ACTIONS and generation_disabled():
            logger.warning(f"⛔ Generation disabled. Rejecting action: {action}")
            return {
                "error": "GENERATION_DISABLED",
                "success": False,
                "message": "AI generation is temporarily disabled.",
                "action": action,
            }
        
        if action == "create_magazine":
            return handle_create_magazine(data)
        elif action == "spring_internal_callback":
            return handle_spring_internal_callback(data)
        elif action == "create_moodboard" or action == "generate_moodboard":
            return handle_create_moodboard(data)
        elif action == "edit_magazine" or action == "chat":
            return handle_edit_magazine(data)
        elif action == "edit_section":
            return handle_edit_section(data)
        elif action == "generate_paragraph":
            return handle_generate_paragraph(data)
        elif action == "health":
            # 상세 헬스체크 - API 설정 상태 포함
            from app.core.llm_client import llm_client
            from app.version import get_runtime_info
            try:
                from app.core.local_diffusion_client import local_diffusion_client
                diffusion_status = local_diffusion_client.get_status()
            except:
                diffusion_status = {"loaded": False, "error": "Import failed"}
            
            return {
                "status": "healthy", 
                "message": "M:ine AI Serverless is running",
                **get_runtime_info(),
                "config_status": {
                    "openai_configured": llm_client.is_configured(),
                    "diffusion_status": diffusion_status
                }
            }
        else:
            return {"error": f"Unknown action: {action}"}
            
    except Exception as e:
        logger.error(f"❌ Handler Error: {e}")
        logger.error(f"📋 Full Traceback:\n{traceback.format_exc()}")
        return {"error": str(e), "traceback": traceback.format_exc()}


def validate_topic(topic: str) -> dict:
    """
    Validate topic for meaningless or harmful keywords.
    Returns None if valid, error dict if invalid.
    """
    if not topic or not topic.strip():
        return {"error": "topic is required"}
    
    topic_stripped = topic.strip()
    
    # 1. Too short (single character / meaningless)
    if len(topic_stripped) <= 1:
        return {"error": "INVALID_TOPIC", "message": "Please provide a more specific topic (at least 2 characters)."}
    
    # 2. Harmful/NSFW keyword blocklist
    blocked_keywords = [
        "nsfw", "porn", "sex", "nude", "naked", "erotic", "hentai",
        "kill", "murder", "suicide", "terrorism", "drug",
        "gore", "torture", "abuse",
    ]
    topic_lower = topic_stripped.lower()
    for keyword in blocked_keywords:
        if keyword in topic_lower:
            return {"error": "BLOCKED_TOPIC", "message": "This topic contains inappropriate content and cannot be used."}
    
    return None


def handle_create_magazine(data: dict) -> dict:
    """
    Handle magazine creation request.
    """
    from app.core.magazine_maker import (
        PARAGRAPH_MAX_CHARS,
        PARAGRAPH_MIN_CHARS,
        generate_magazine_content,
    )
    from app.version import get_runtime_info
    handler_start = time.perf_counter()
    request_id = data.get("request_id") or str(uuid.uuid4())[:8]
    
    topic = data.get("topic")
    user_interests = data.get("user_interests", [])
    user_mood = data.get("user_mood")
    
    # Pre-filtering: block nonsense and harmful topics
    validation_error = validate_topic(topic)
    if validation_error:
        return validation_error
    
    logger.info(f"📰 Creating magazine for topic: {topic}")
    logger.info(f"📰 create_magazine request_id={request_id}")
    runtime_info = get_runtime_info()
    logger.info(
        f"[create_magazine][request_id={request_id}] runtime: "
        f"git_commit={runtime_info.get('git_commit')} "
        f"paragraph_min_chars={PARAGRAPH_MIN_CHARS} "
        f"paragraph_max_chars={PARAGRAPH_MAX_CHARS}"
    )
    if user_mood:
        logger.info(f"🎭 User mood: {user_mood}")
    
    result = generate_magazine_content(
        topic=topic,
        user_interests=user_interests,
        user_mood=user_mood,
        request_id=request_id,
        runpod_handler_start_time=time.perf_counter() - handler_start
    )
    
    if not result:
        return {"error": "Failed to generate magazine"}

    logger.info(
        f"[create_magazine][request_id={request_id}] "
        "Spring internal callback forcibly disabled for create_magazine"
    )
    
    return result


def handle_spring_internal_callback(data: dict) -> dict:
    """
    Explicit internal-only callback action.
    create_magazine never calls this path, regardless of env flags.
    """
    request_id = data.get("request_id") or str(uuid.uuid4())[:8]
    if data.get("internal_mode") is not True:
        return {
            "error": "INTERNAL_MODE_REQUIRED",
            "message": "spring_internal_callback requires internal_mode=true",
        }

    payload_source = data.get("payload") or data.get("magazine") or data
    payload, had_base64 = _sanitize_callback_payload(payload_source)
    payload_bytes = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    logger.info(
        f"[spring_internal_callback][request_id={request_id}] payload_check: "
        f"payload_bytes={payload_bytes}, payload_had_base64={had_base64}"
    )
    if had_base64:
        logger.error(
            f"[spring_internal_callback][request_id={request_id}] rejected: "
            "payload_had_base64=True"
        )
        return {
            "error": "CALLBACK_PAYLOAD_CONTAINED_BASE64",
            "message": "callback payload must not contain data:image base64 fields",
            "payload_had_base64": True,
            "payload_bytes": payload_bytes,
        }

    try:
        from app.core.spring_internal_client import SpringInternalClient
        client = SpringInternalClient.from_env()
        if client is None:
            return {"error": "SPRING_INTERNAL_CLIENT_NOT_CONFIGURED"}

        user_email = data.get("user_email") or payload.get("userEmail") or payload.get("user_email")
        if user_email and "userEmail" not in payload:
            payload["userEmail"] = user_email
            payload_bytes = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

        callback_start = time.perf_counter()
        response = client.post_internal("/api/internal/magazine", payload)
        callback_time = round(time.perf_counter() - callback_start, 3)
        logger.info(
            f"[spring_internal_callback][request_id={request_id}] callback_timing: "
            f"spring_callback_success=true spring_callback_time={callback_time} "
            f"spring_callback_payload_bytes={payload_bytes} spring_callback_payload_had_base64=false"
        )
        return {
            "success": True,
            "spring_callback_time": callback_time,
            "spring_callback_payload_bytes": payload_bytes,
            "spring_callback_payload_had_base64": False,
            "spring_response": response,
        }
    except Exception as e:
        logger.error(f"❌ Explicit Spring internal callback failed: {e}")
        return {
            "error": "SPRING_INTERNAL_CALLBACK_FAILED",
            "message": str(e),
            "spring_callback_payload_bytes": payload_bytes,
            "spring_callback_payload_had_base64": False,
        }


def handle_create_moodboard(data: dict) -> dict:
    """
    Handle moodboard creation request.
    Returns structured response with success indicator.
    
    On success: {"image_url": "...", "description": "...", "success": True}
    On failure: {"image_url": None, "fallback_url": None, "success": False, "error_type": "..."}
    """
    logger.info("🎨 [1/4] Moodboard handler started")
    logger.info(f"🎨 [1/4] Data received: {data}")
    
    try:
        logger.info("🎨 [2/4] Importing generate_moodboard...")
        from app.core.moodboard_maker import generate_moodboard
        logger.info("🎨 [2/4] Import successful")
        
        logger.info("🎨 [3/4] Calling generate_moodboard...")
        result = generate_moodboard(
            topic=data.get("topic"),
            user_mood=data.get("user_mood"),
            user_interests=data.get("user_interests"),
            magazine_tags=data.get("magazine_tags"),
            magazine_titles=data.get("magazine_titles"),
            section_headings=data.get("section_headings"),
            content_keywords=data.get("content_keywords"),
        )
        
        # 결과 검증 (None 체크 + image_url 존재 여부)
        if not result:
            logger.warning("🎨 [4/4] Result is None, returning error")
            return {
                "error": "Failed to generate moodboard - no result returned",
                "success": False,
                "image_url": None,
                "fallback_url": None,
            }
        
        # success 필드 확인 (새로운 응답 형식)
        if result.get("success") is False:
            logger.warning(f"🎨 [4/4] Moodboard failed without usable fallback: {result.get('error_type')}")
        else:
            logger.info("🎨 [4/4] Success! Generated with SDXL")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Moodboard Error: {e}")
        logger.error(f"📋 Traceback:\n{traceback.format_exc()}")
        return {
            "error": str(e), 
            "success": False,
            "traceback": traceback.format_exc(),
            "image_url": None,
            "fallback_url": None,
        }


def handle_edit_magazine(data: dict) -> dict:
    """
    Handle magazine editing/chat request.
    Uses magazine_editor to modify existing magazines based on user instructions.
    """
    logger.info("💬 [1/4] Edit magazine handler started")
    logger.info(f"💬 [1/4] Data received: {data}")
    
    try:
        from app.core.magazine_editor import (
            analyze_user_intent,
            regenerate_section,
            add_new_section,
            change_overall_tone
        )
        logger.info("💬 [2/4] Imports successful")
        
        message = data.get("message", "")
        magazine_data = data.get("magazine_data", {})
        
        if not message:
            return {"error": "message is required"}
        if not magazine_data:
            return {"error": "magazine_data is required"}
        
        logger.info(f"💬 [3/4] Analyzing intent for: {message[:50]}...")
        
        # 1. 사용자 의도 분석
        intent = analyze_user_intent(message, magazine_data)
        logger.info(f"💬 [3/4] Intent: {intent}")
        
        # 2. 의도에 따른 처리
        result = None
        new_sections = []
        deleted_section_ids = []
        
        if intent.action == "regenerate_section":
            # ⭐ Fix: target_section_index가 None이면 regenerate 불가 → add_section으로 처리
            if intent.target_section_index is None:
                logger.warning(f"⚠️ regenerate_section 요청이지만 target_section_index=None → add_section으로 처리: {message[:50]}")
                result = add_new_section(magazine_data, intent.instruction or message)
                new_sections = [result] if result else []
            else:
                result = regenerate_section(
                    magazine_data,
                    intent.target_section_index,
                    intent.instruction
                )
                new_sections = [result] if result else []
        elif intent.action == "add_section":
            result = add_new_section(magazine_data, intent.instruction)
            if isinstance(result, dict) and result.get("success") is False:
                return {
                    "intent": "add_section",
                    "success": False,
                    "error": result.get("error", "EDIT_REJECTED"),
                    "message": result.get("message", "요청한 내용을 검증할 수 없어 섹션을 추가하지 않았습니다."),
                    "updated_magazine": None,
                }
            new_sections = [result] if result else []
        elif intent.action == "delete_section":
            # 삭제 대상 섹션 ID 추출
            if intent.target_section_index is not None:
                sections = magazine_data.get('sections', [])
                if 0 <= intent.target_section_index < len(sections):
                    deleted_section_ids = [sections[intent.target_section_index].get('id')]
        elif intent.action == "change_tone":
            result = change_overall_tone(magazine_data, intent.instruction)
            if isinstance(result, list):
                rejected = next((item for item in result if isinstance(item, dict) and item.get("success") is False), None)
                if rejected:
                    return {
                        "intent": "change_tone",
                        "success": False,
                        "error": rejected.get("error", "EDIT_REJECTED"),
                        "message": rejected.get("message", "요청한 내용을 검증할 수 없어 톤 변경을 적용하지 않았습니다."),
                        "updated_magazine": None,
                    }
            new_sections = result if isinstance(result, list) else []
        else:
            # 기본: 전체 톤 변경으로 처리
            result = change_overall_tone(magazine_data, message)
            new_sections = result if isinstance(result, list) else []

        
        logger.info(f"💬 [4/4] Result: {result is not None or len(deleted_section_ids) > 0}")
        
        # Spring이 기대하는 응답 형식
        return {
            "intent": intent.action if intent else "no_change",
            "success": True,
            "updated_magazine": {
                "heading": intent.response_message if intent else "수정이 완료되었습니다",
                "new_sections": new_sections,
                "deleted_section_ids": deleted_section_ids
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Edit Magazine Error: {e}")
        logger.error(f"📋 Traceback:\n{traceback.format_exc()}")
        return {
            "intent": "no_change",
            "success": False,
            "error": str(e),
            "updated_magazine": None
        }


def handle_edit_section(data: dict) -> dict:
    """
    Handle section-level editing request.
    Spring sends this via POST /api/magazines/{magazineId}/sections/{sectionId}/interact
    
    Expected data format:
    {
        "magazine_id": 1,
        "section_id": 101,
        "section_data": {
            "id": 101,
            "heading": "...",
            "content": "<p>...</p>",
            "image_url": "...",
            "layout_hint": "...",
            "layout_type": "...",
            "caption": "..."
        },
        "message": "이 내용 좀 더 감성적으로 바꿔줘"
    }
    
    Returns (Spring-compatible):
    {
        "intent": "edit_content",
        "success": True,
        "updated_section": { ... }
    }
    """
    logger.info("✏️ [1/3] Edit section handler started")
    logger.info(f"✏️ [1/3] Data received: {data}")
    
    try:
        from app.core.magazine_editor import edit_section_content
        logger.info("✏️ [2/3] Import successful")
        
        section_data = data.get("section_data", {})
        message = data.get("message", "")
        
        if not section_data:
            return {"error": "section_data is required", "success": False}
        if not message:
            return {"error": "message is required", "success": False}
        
        logger.info(f"✏️ [2/3] Editing section: {section_data.get('heading', 'N/A')[:30]}")
        logger.info(f"✏️ [2/3] User request: {message[:50]}...")
        
        # 매거진 주제 추출 (할루시네이션 방지를 위해 topic 전달)
        magazine_title = data.get("magazine_title", "")  # Spring에서 전달받음
        topic = magazine_title if magazine_title else section_data.get('heading', 'Magazine Content')
        
        # 섹션 레벨 편집 수행
        result = edit_section_content(section_data, message, topic=topic)
        
        logger.info(f"✏️ [3/3] Result success: {result.get('success', False)}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Edit Section Error: {e}")
        logger.error(f"📋 Traceback:\n{traceback.format_exc()}")
        return {
            "intent": "edit_content",
            "success": False,
            "error": str(e),
            "updated_section": None
        }


def handle_generate_paragraph(data: dict) -> dict:
    """
    Handle paragraph generation request for RunPod.
    """
    logger.info("📝 [1/3] Generate paragraph handler started")
    logger.info(f"📝 [1/3] Data received: {data}")
    
    try:
        from app.core.magazine_editor import generate_paragraph
        logger.info("📝 [2/3] Import successful")
        
        topic = data.get("topic", "")
        section_heading = data.get("section_heading", "")
        message = data.get("message", "")
        user_mood = data.get("user_mood", "")
        existing_paragraphs = data.get("existing_paragraphs", [])
        
        if not message:
            return {"error": "message is required", "success": False}
        
        logger.info(f"📝 [2/3] Generating paragraph for: {message[:50]}...")
        
        result = generate_paragraph(
            topic=topic,
            section_heading=section_heading,
            message=message,
            user_mood=user_mood,
            existing_paragraphs=existing_paragraphs
        )
        
        logger.info(f"📝 [3/3] Result success")
        return result
        
    except Exception as e:
        logger.error(f"❌ Generate Paragraph Error: {e}")
        import traceback
        logger.error(f"📋 Traceback:\n{traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e)
        }



# Start the RunPod serverless worker
if __name__ == "__main__":
    logger.info("🎯 Starting M:ine AI Serverless Worker...")
    runpod.serverless.start({"handler": handler})
