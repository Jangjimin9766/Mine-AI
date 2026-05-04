from app.core import magazine_maker
from app.core import moodboard_maker


def _valid_magazine_json():
    return {
        "title": "홈 오피스 생산성 셋업",
        "cover_image_url": None,
        "tags": ["LIFESTYLE", "INTERIOR"],
        "sections": [
            {
                "heading": "집중을 만드는 책상",
                "thumbnail_url": None,
                "display_order": 0,
                "paragraphs": [
                    {
                        "subtitle": "조명의 기준",
                        "text": "문단 본문입니다. " * 40,
                        "image_search_keyword": "home office lighting",
                        "source_url": "https://example.com/a",
                        "image_url": None,
                    },
                    {
                        "subtitle": "동선의 기준",
                        "text": "문단 본문입니다. " * 40,
                        "image_search_keyword": "home office desk",
                        "source_url": "https://example.com/b",
                        "image_url": None,
                    },
                    {
                        "subtitle": "정리의 기준",
                        "text": "문단 본문입니다. " * 40,
                        "image_search_keyword": "organized desk",
                        "source_url": "https://example.com/a",
                        "image_url": None,
                    },
                ],
            },
            {
                "heading": "지속 가능한 루틴",
                "thumbnail_url": None,
                "display_order": 1,
                "paragraphs": [
                    {
                        "subtitle": "시간의 기준",
                        "text": "문단 본문입니다. " * 40,
                        "image_search_keyword": "daily routine desk",
                        "source_url": "https://example.com/c",
                        "image_url": None,
                    },
                    {
                        "subtitle": "소음의 기준",
                        "text": "문단 본문입니다. " * 40,
                        "image_search_keyword": "quiet home office",
                        "source_url": "https://example.com/d",
                        "image_url": None,
                    },
                    {
                        "subtitle": "휴식의 기준",
                        "text": "문단 본문입니다. " * 40,
                        "image_search_keyword": "home office break",
                        "source_url": "https://example.com/c",
                        "image_url": None,
                    },
                ],
            },
        ],
    }


class MockLLM:
    def __init__(self, result):
        self.result = result
        self.call_count = 0

    def generate_json(self, *args, **kwargs):
        self.call_count += 1
        assert kwargs.get("response_format") == magazine_maker.MAGAZINE_RESPONSE_FORMAT
        return self.result


def test_create_magazine_does_not_repair_valid_contract(monkeypatch, capsys):
    mock_llm = MockLLM(_valid_magazine_json())
    monkeypatch.setattr(magazine_maker, "llm_client", mock_llm)
    monkeypatch.setattr(
        magazine_maker,
        "search_with_tavily",
        lambda *args, **kwargs: (
            [
                {"url": "https://example.com/a", "content": "a"},
                {"url": "https://example.com/b", "content": "b"},
                {"url": "https://example.com/c", "content": "c"},
            ],
            ["https://example.com/cover.jpg"],
        ),
    )
    monkeypatch.setattr(
        magazine_maker,
        "scrape_labeled_sources",
        lambda *args, **kwargs: (
            [("https://example.com/a", "a"), ("https://example.com/b", "b")],
            ["https://example.com/img1.jpg", "https://example.com/img2.jpg"],
        ),
    )
    monkeypatch.setattr(magazine_maker, "validate_image_url", lambda url: True)
    monkeypatch.setattr(magazine_maker, "search_with_pexels", lambda *args, **kwargs: ["https://example.com/pexels.jpg"])
    monkeypatch.setattr(magazine_maker, "_expand_short_paragraphs", lambda result_json, topic, labeled_material: result_json)

    def fail_repair(*args, **kwargs):
        raise AssertionError("contract repair should not be called")

    monkeypatch.setattr(magazine_maker, "_repair_magazine_contract", fail_repair)
    monkeypatch.setattr(
        moodboard_maker,
        "generate_moodboard",
        lambda **kwargs: {
            "image_url": "https://example.com/moodboard.png",
            "description": "premium editorial moodboard",
            "success": True,
            "timing": {"moodboard_generation_time": 0.01},
        },
    )

    result = magazine_maker.generate_magazine_content("홈 오피스", request_id="test-no-repair")

    assert len(result["sections"]) == 2
    assert [len(section["paragraphs"]) for section in result["sections"]] == [3, 3]
    assert result["moodboard"]["image_url"]
    assert result["moodboard"]["description"]

    output = capsys.readouterr().out
    assert '"contract_repair_needed": false' in output
    assert '"openai_call_count": 1' in output


def test_repair_reason_detection_and_local_fix():
    broken = {
        "sections": [
            {
                "heading": "섹션",
                "paragraphs": [
                    {"subtitle": "소제목", "text": "짧음"},
                    {"subtitle": "소제목", "text": "짧음"},
                ],
            }
        ]
    }
    before = magazine_maker._repair_reasons(broken)
    assert "section_count_mismatch" in before
    assert "paragraph_count_mismatch" in before
    assert "missing_source_url" in before
    assert "missing_image_url" in before
    assert "paragraph_too_short" in before

    fixed = magazine_maker._apply_local_contract_fixes(
        broken,
        "홈 오피스",
        [("https://example.com/a", "a")],
        [{"url": "https://example.com/fallback"}],
    )
    after = magazine_maker._repair_reasons(fixed)
    assert "missing_source_url" not in after
    assert "missing_image_url" not in after
