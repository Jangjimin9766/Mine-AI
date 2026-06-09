from app.core import magazine_editor
from app.core import searcher
from app.core import llm_client as llm_client_module
import json
import threading
import time


def test_add_new_section_rejects_youtuber_recommendation_without_sources(monkeypatch):
    monkeypatch.setattr(
        searcher,
        "search_with_tavily",
        lambda *args, **kwargs: ([], []),
    )

    result = magazine_editor.add_new_section(
        {"title": "세계여행", "sections": []},
        "여행 유튜버 추천 문단 추가해줘",
    )

    assert result["success"] is False
    assert result["error"] == "INSUFFICIENT_VERIFIED_SOURCES"


def test_add_new_section_rejects_unverified_source_url(monkeypatch):
    monkeypatch.setattr(
        searcher,
        "search_with_tavily",
        lambda *args, **kwargs: (
            [{"url": "https://verified.example/travel", "content": "검증된 여행 채널 정보"}],
            [],
        ),
    )
    monkeypatch.setattr(
        searcher,
        "scrape_labeled_sources",
        lambda *args, **kwargs: ([("https://verified.example/travel", "검증된 여행 채널 정보")], []),
    )
    monkeypatch.setattr(searcher, "search_with_pexels", lambda *args, **kwargs: [])

    class FakeLLM:
        def generate_json(self, *args, **kwargs):
            return {
                "heading": "여행 채널 큐레이션",
                "paragraphs": [
                    {
                        "subtitle": "없는 채널",
                        "text": "검증되지 않은 여행 유튜버를 추천하는 문단입니다.",
                        "image_search_keyword": "travel creator",
                        "source_url": "https://made-up.example/channel",
                    }
                ],
            }

    monkeypatch.setattr(llm_client_module, "llm_client", FakeLLM())

    result = magazine_editor.add_new_section(
        {"title": "세계여행", "sections": []},
        "여행 유튜버 추천 문단 추가해줘",
    )

    assert result["success"] is False
    assert result["error"] == "INSUFFICIENT_VERIFIED_SOURCES"
    assert result["reason"].startswith("UNVERIFIED_SOURCE")


def test_add_new_section_retries_once_after_invalid_llm_json(monkeypatch):
    monkeypatch.setattr(searcher, "search_with_tavily", lambda *args, **kwargs: ([], []))
    monkeypatch.setattr(searcher, "search_with_pexels", lambda *args, **kwargs: [])

    calls = []

    def generate_json(*args, **kwargs):
        calls.append(kwargs.get("temperature"))
        if len(calls) == 1:
            raise json.JSONDecodeError("invalid", "", 0)
        return {"heading": "새로운 관점", "paragraphs": []}

    monkeypatch.setattr(magazine_editor.llm_client, "generate_json", generate_json)

    result = magazine_editor.add_new_section(
        {"title": "생활", "sections": []},
        "새로운 관점 추가",
    )

    assert result["heading"] == "새로운 관점"
    assert calls == [0.7, 0.3]


def test_generated_section_strips_numbered_subtitle_prefix():
    result = magazine_editor.sanitize_generated_section({
        "heading": "아이브의 초창기",
        "paragraphs": [{"subtitle": "소제목 1: 데뷔의 시작", "text": "완성된 본문"}],
    })

    assert result["paragraphs"][0]["subtitle"] == "데뷔의 시작"


def test_generated_section_rejects_exact_placeholders():
    assert magazine_editor.contains_section_placeholders({
        "heading": "섹션 제목",
        "paragraphs": [{"subtitle": "소제목 1", "text": "본문 1"}],
    }) is True


def test_add_new_section_parallelizes_scraping_and_preserves_source_order(monkeypatch):
    urls = [f"https://source.example/{i}" for i in range(3)]
    monkeypatch.setattr(searcher, "search_with_tavily", lambda *args, **kwargs: (
        [{"url": url, "content": f"fallback-{i}"} for i, url in enumerate(urls)],
        [],
    ))
    barrier = threading.Barrier(3)

    def scrape(url_list, max_count):
        barrier.wait(timeout=1)
        url = url_list[0]
        time.sleep(0.01 * (3 - urls.index(url)))
        return [(url, f"scraped-{url}")], []

    monkeypatch.setattr(searcher, "scrape_labeled_sources", scrape)
    monkeypatch.setattr(searcher, "search_with_pexels", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        magazine_editor.llm_client,
        "generate_json",
        lambda system, user, **kwargs: {
            "heading": "새 섹션",
            "paragraphs": [
                {"subtitle": f"문단 {i}", "text": "완성된 본문", "image_search_keyword": f"image {i}"}
                for i in range(3)
            ],
        },
    )

    result = magazine_editor.add_new_section({"title": "생활", "sections": []}, "새 섹션 추가")

    assert [para["source_url"] for para in result["paragraphs"]] == urls


def test_add_new_section_parallel_image_search_preserves_order_and_fallback(monkeypatch):
    monkeypatch.setattr(searcher, "search_with_tavily", lambda *args, **kwargs: ([], ["tavily-fallback"]))
    barrier = threading.Barrier(4)

    def search_image(keyword, **kwargs):
        barrier.wait(timeout=1)
        return [] if keyword == "image 1" else [f"pexels-{keyword}"]

    monkeypatch.setattr(searcher, "search_with_pexels", search_image)
    monkeypatch.setattr(
        magazine_editor.llm_client,
        "generate_json",
        lambda system, user, **kwargs: {
            "heading": "새 섹션",
            "paragraphs": [
                {"subtitle": f"문단 {i}", "text": "완성된 본문", "image_search_keyword": f"image {i}"}
                for i in range(3)
            ],
        },
    )

    result = magazine_editor.add_new_section({"title": "생활", "sections": []}, "새 섹션 추가")

    assert [para["image_url"] for para in result["paragraphs"]] == [
        "pexels-image 0",
        "tavily-fallback",
        "pexels-image 2",
    ]
    assert result["thumbnail_url"] == "pexels-새 섹션"


def test_add_new_section_scrape_failure_keeps_original_source_position(monkeypatch):
    urls = [f"https://source.example/{i}" for i in range(3)]
    monkeypatch.setattr(searcher, "search_with_tavily", lambda *args, **kwargs: (
        [{"url": url, "content": f"fallback-{i}"} for i, url in enumerate(urls)],
        [],
    ))
    monkeypatch.setattr(
        searcher,
        "scrape_labeled_sources",
        lambda url_list, max_count: ([], []) if url_list[0] == urls[0] else ([(url_list[0], "scraped")], []),
    )
    monkeypatch.setattr(searcher, "search_with_pexels", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        magazine_editor.llm_client,
        "generate_json",
        lambda system, user, **kwargs: {
            "heading": "새 섹션",
            "paragraphs": [
                {"subtitle": f"문단 {i}", "text": "완성된 본문", "image_search_keyword": f"image {i}"}
                for i in range(3)
            ],
        },
    )

    result = magazine_editor.add_new_section({"title": "생활", "sections": []}, "새 섹션 추가")

    assert [para["source_url"] for para in result["paragraphs"]] == urls
