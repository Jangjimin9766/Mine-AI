"""서비스 초기화용 더미 매거진 생성 스크립트.

기본 동작:
1) Mine-AI /api/magazine/create(create_magazine) 호출로 매거진 15개 생성
2) 결과를 JSON 파일로 저장
3) (선택) Mine-server 내부 관리 API로 벌크 업로드

환경변수:
- MINE_AI_URL (default: http://localhost:8000)
- MINE_SERVER_BULK_URL (optional)
- MINE_SERVER_BEARER_TOKEN (optional)
- MINE_INTERNAL_SECRET_KEY (optional; for /api/internal/* endpoints)
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

import requests


@dataclass
class DummyUserPlan:
    email: str
    interests: List[str]
    topics: List[str]
    mood: str


DUMMY_PLANS: List[DummyUserPlan] = [
    DummyUserPlan(
        email="starter.sports@mine.local",
        interests=["SPORTS", "FITNESS", "HEALTH"],
        topics=["러닝화 트렌드 2026", "실내 클라이밍 입문 가이드", "회복 루틴과 스트레칭"],
        mood="Bold",
    ),
    DummyUserPlan(
        email="starter.fashion@mine.local",
        interests=["FASHION", "BEAUTY", "ACCESSORY"],
        topics=["2026 봄 미니멀 룩북", "데일리 향수 레이어링", "빈티지 액세서리 큐레이션"],
        mood="Classic",
    ),
    DummyUserPlan(
        email="starter.tech@mine.local",
        interests=["TECH", "IT", "ELECTRONICS"],
        topics=["온디바이스 AI 시대의 스마트폰", "생산성 키보드·마우스 셋업", "홈 오피스 오디오 업그레이드"],
        mood="Minimal",
    ),
    DummyUserPlan(
        email="starter.travel@mine.local",
        interests=["TRAVEL", "FOOD", "CULTURE"],
        topics=["주말 기차 여행 도시 3선", "로컬 브런치 스폿 아카이브", "소도시 야시장 미식 노트"],
        mood="Fun",
    ),
    DummyUserPlan(
        email="starter.art@mine.local",
        interests=["ART", "DESIGN", "PHOTOGRAPHY"],
        topics=["독립 전시 공간 탐방", "포토워크를 위한 카메라 세팅", "인테리어와 아트 포스터 매칭"],
        mood="Classic",
    ),
]


def generate_magazine(ai_url: str, plan: DummyUserPlan, topic: str) -> Dict[str, Any]:
    endpoint = f"{ai_url.rstrip('/')}/api/magazine/create"
    payload = {
        "action": "create_magazine",
        "topic": topic,
        "user_email": plan.email,
        "user_mood": plan.mood,
        "user_interests": plan.interests,
    }
    response = requests.post(endpoint, json=payload, timeout=180)
    response.raise_for_status()
    data = response.json()
    data["seed_user_email"] = plan.email
    data["seed_topic"] = topic
    data["seed_interests"] = plan.interests
    return data


def maybe_upload_to_server(seed_data: List[Dict[str, Any]]) -> None:
    bulk_url = os.getenv("MINE_SERVER_BULK_URL")
    if not bulk_url:
        print("ℹ️ MINE_SERVER_BULK_URL 미설정: 로컬 JSON만 생성합니다.")
        return

    headers = {"Content-Type": "application/json"}
    token = os.getenv("MINE_SERVER_BEARER_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    internal_key = os.getenv("MINE_INTERNAL_SECRET_KEY")
    if internal_key and "/api/internal/" in bulk_url:
        headers["X-Internal-Key"] = internal_key

    payload = {"items": seed_data, "source": "mine-ai-bootstrap-script"}
    response = requests.post(bulk_url, json=payload, headers=headers, timeout=120)
    response.raise_for_status()
    print(f"✅ Mine-server 업로드 성공: {bulk_url}")


def main() -> None:
    ai_url = os.getenv("MINE_AI_URL", "http://localhost:8000")
    out_path = Path("tools/out/initial_dummy_magazines.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_magazines: List[Dict[str, Any]] = []
    for plan in DUMMY_PLANS:
        for topic in plan.topics:
            print(f"🧪 생성 중: {plan.email} | {topic}")
            item = generate_magazine(ai_url, plan, topic)
            all_magazines.append(item)
            time.sleep(0.5)

    with out_path.open("w", encoding="utf-8") as fp:
        json.dump(all_magazines, fp, ensure_ascii=False, indent=2)

    print(f"✅ 더미 데이터 생성 완료: users={len(DUMMY_PLANS)}, magazines={len(all_magazines)}")
    print(f"📦 저장 파일: {out_path}")

    maybe_upload_to_server(all_magazines)


if __name__ == "__main__":
    main()
