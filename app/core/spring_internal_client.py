from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from app.core.logging_config import get_logger
from app.config import settings

logger = get_logger("spring-internal-client")


@dataclass(frozen=True)
class SpringInternalClientConfig:
    base_url: str
    internal_key: str
    timeout_seconds: int = 15
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0


class SpringInternalClient:
    """
    Mine-server internal API client.
    Standardizes X-Internal-Key header + timeouts + simple retries.
    """

    def __init__(self, config: SpringInternalClientConfig):
        self._config = config

    @classmethod
    def from_env(cls) -> Optional["SpringInternalClient"]:
        base_url = (os.getenv("SPRING_API_URL") or getattr(settings, "SPRING_API_URL", "") or "").strip().rstrip("/")
        internal_key = (os.getenv("MINE_INTERNAL_SECRET_KEY") or getattr(settings, "MINE_INTERNAL_SECRET_KEY", "") or "").strip()

        if not base_url or not internal_key:
            return None

        return cls(
            SpringInternalClientConfig(
                base_url=base_url,
                internal_key=internal_key,
                timeout_seconds=int(os.getenv("SPRING_INTERNAL_TIMEOUT", "15")),
                max_retries=int(os.getenv("SPRING_INTERNAL_MAX_RETRIES", "3")),
                retry_backoff_seconds=float(os.getenv("SPRING_INTERNAL_RETRY_BACKOFF", "1.0")),
            )
        )

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Internal-Key": self._config.internal_key,
        }

    def post_internal(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._config.base_url}{path}"
        last_exc: Optional[Exception] = None

        for attempt in range(1, self._config.max_retries + 1):
            try:
                resp = requests.post(url, json=payload, headers=self._headers(), timeout=self._config.timeout_seconds)
                if resp.status_code == 403:
                    raise RuntimeError("Forbidden (X-Internal-Key mismatch)")
                resp.raise_for_status()
                # internal endpoints often return plain strings/ids
                try:
                    return {"ok": True, "status": resp.status_code, "json": resp.json()}
                except Exception:
                    return {"ok": True, "status": resp.status_code, "text": resp.text}
            except Exception as e:
                last_exc = e
                if attempt >= self._config.max_retries:
                    break
                sleep_s = self._config.retry_backoff_seconds * attempt
                logger.warning(f"Spring internal call failed (attempt {attempt}/{self._config.max_retries}): {e}. Retrying in {sleep_s}s")
                time.sleep(sleep_s)

        raise RuntimeError(f"Spring internal call failed after retries: {last_exc}")

