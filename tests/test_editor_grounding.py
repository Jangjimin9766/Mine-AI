from app.core import magazine_editor
from app.core import searcher
from app.core import llm_client as llm_client_module


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
