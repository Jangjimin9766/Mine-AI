"""
Better Stack (Logtail) 로깅 설정
팀원들이 웹 대시보드에서 실시간으로 로그를 볼 수 있도록 함
"""
import logging
import sys
import os

# Logtail 핸들러는 선택적으로 로드 (패키지가 없어도 동작)
try:
    from logtail import LogtailHandler
    LOGTAIL_AVAILABLE = True
except ImportError:
    LOGTAIL_AVAILABLE = False
    LogtailHandler = None


def get_logger(name: str, level=logging.INFO) -> logging.Logger:
    """
    로거를 생성하고 반환합니다.
    
    - 콘솔 출력: 항상 활성화
    - Logtail 출력: LOGTAIL_SOURCE_TOKEN이 설정된 경우에만 활성화
    
    Args:
        name: 로거 이름 (보통 __name__ 사용)
        level: 로깅 레벨 (기본: INFO)
    
    Returns:
        설정된 Logger 인스턴스
    """
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 있으면 재설정하지 않음
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # 콘솔 핸들러 (항상 활성화)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # Logtail 핸들러 (토큰이 있을 때만 활성화)
    source_token = os.getenv("LOGTAIL_SOURCE_TOKEN", "")
    
    if LOGTAIL_AVAILABLE and source_token:
        try:
            logtail_host = os.getenv("LOGTAIL_HOST", "s1876389.eu-nbg-2.betterstackdata.com")
            logtail_handler = LogtailHandler(
                source_token=source_token,
                host=f"https://{logtail_host}"
            )
            logtail_handler.setLevel(level)
            logger.addHandler(logtail_handler)
            logger.info(f"✅ Logtail 로깅 활성화 (host: {logtail_host})")
        except Exception as e:
            logger.warning(f"⚠️ Logtail 설정 실패: {e}, 콘솔 로깅만 사용합니다")
    elif not source_token:
        logger.debug("ℹ️ LOGTAIL_SOURCE_TOKEN이 설정되지 않음, 콘솔 로깅만 사용")
    
    return logger


# 기본 로거 (모듈 레벨에서 사용 가능)
logger = get_logger("mine-ai")
