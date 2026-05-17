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
                        "text": "문단 본문입니다. " * 50,
                        "image_search_keyword": "home office lighting",
                        "source_url": "https://example.com/a",
                        "image_url": None,
                    },
                    {
                        "subtitle": "동선의 기준",
                        "text": "문단 본문입니다. " * 50,
                        "image_search_keyword": "home office desk",
                        "source_url": "https://example.com/b",
                        "image_url": None,
                    },
                    {
                        "subtitle": "정리의 기준",
                        "text": "문단 본문입니다. " * 50,
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
                        "text": "문단 본문입니다. " * 50,
                        "image_search_keyword": "daily routine desk",
                        "source_url": "https://example.com/c",
                        "image_url": None,
                    },
                    {
                        "subtitle": "소음의 기준",
                        "text": "문단 본문입니다. " * 50,
                        "image_search_keyword": "quiet home office",
                        "source_url": "https://example.com/d",
                        "image_url": None,
                    },
                    {
                        "subtitle": "휴식의 기준",
                        "text": "문단 본문입니다. " * 50,
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
    assert '"targeted_expansion_needed": false' in output
    assert '"targeted_expansion_count": 0' in output
    assert '"initial_paragraph_lengths":' in output
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
    assert "paragraph_too_short" in after


def test_paragraph_too_short_uses_targeted_expansion(monkeypatch):
    magazine = _valid_magazine_json()
    magazine["sections"][0]["paragraphs"][1]["text"] = "짧은 문단입니다."
    full_repair_called = False

    def fail_full_repair(*args, **kwargs):
        nonlocal full_repair_called
        full_repair_called = True
        raise AssertionError("full contract repair should not be called for paragraph_too_short only")

    def targeted_expand(system_prompt, user_prompt, temperature=0.7, response_format=None):
        return [
            {
                "section": 0,
                "paragraph": 1,
                "text": "확장된 문단입니다. " * 80,
            }
        ]

    mock_llm = MockLLM(magazine)
    mock_llm.generate_json = targeted_expand
    monkeypatch.setattr(magazine_maker, "llm_client", mock_llm)
    monkeypatch.setattr(magazine_maker, "_repair_magazine_contract", fail_full_repair)

    reasons = magazine_maker._repair_reasons(magazine)
    shorts = magazine_maker._short_paragraphs(magazine)
    assert reasons == ["paragraph_too_short"]
    assert len(shorts) == 1
    assert magazine_maker._needs_contract_repair(magazine, reasons) is False

    expanded = magazine_maker._expand_short_paragraphs(magazine, "홈 오피스", "research")
    assert full_repair_called is False
    assert magazine_maker._paragraph_length(expanded["sections"][0]["paragraphs"][1]["text"]) >= magazine_maker.PARAGRAPH_MIN_CHARS


def test_paragraph_length_metric_is_python_len():
    text = "**강조** 문단입니다. English text"

    assert magazine_maker._paragraph_length(text) == len(text)


def test_realistic_paragraph_threshold_targets_only_under_250():
    magazine = _valid_magazine_json()
    lengths = [275, 235, 235, 258, 238, 230]
    paragraphs = [
        para
        for section in magazine["sections"]
        for para in section["paragraphs"]
    ]
    for para, length in zip(paragraphs, lengths):
        para["text"] = "가" * length

    shorts = magazine_maker._short_paragraphs(magazine)

    assert magazine_maker.PARAGRAPH_MIN_CHARS == 250
    assert [item["length"] for item in shorts] == [235, 235, 238, 230]
    assert all(item["min"] == 250 for item in shorts)


def test_targeted_expansion_caps_to_three_shortest(monkeypatch):
    magazine = _valid_magazine_json()
    lengths = [275, 235, 235, 258, 238, 230]
    paragraphs = [
        para
        for section in magazine["sections"]
        for para in section["paragraphs"]
    ]
    for para, length in zip(paragraphs, lengths):
        para["text"] = "가" * length

    expanded_targets = []

    def targeted_expand(system_prompt, user_prompt, temperature=0.7, response_format=None):
        import json
        import re

        match = re.search(r"\[Short Paragraph Targets\]\s*(\[.*?\])\s*\n\s*\[Rules\]", user_prompt, re.S)
        targets = json.loads(match.group(1))
        expanded_targets.extend((item["section"], item["paragraph"], item["length"]) for item in targets)
        return [
            {
                "section": item["section"],
                "paragraph": item["paragraph"],
                "text": "확장된 문단입니다. " * 40,
            }
            for item in targets
        ]

    mock_llm = MockLLM(magazine)
    mock_llm.generate_json = targeted_expand
    monkeypatch.setattr(magazine_maker, "llm_client", mock_llm)

    shorts = magazine_maker._short_paragraphs(magazine)
    expanded = magazine_maker._expand_short_paragraphs(magazine, "홈 오피스", "research", short_items=shorts)

    assert len(expanded_targets) == 3
    assert [target[2] for target in expanded_targets] == [230, 235, 235]
    remaining = magazine_maker._short_paragraphs(expanded)
    assert [item["length"] for item in remaining] == [238]


def test_second_operational_distribution_targets_two_or_fewer():
    magazine = _valid_magazine_json()
    lengths = [300, 280, 274, 263, 240, 220]
    paragraphs = [
        para
        for section in magazine["sections"]
        for para in section["paragraphs"]
    ]
    for para, length in zip(paragraphs, lengths):
        para["text"] = "가" * length

    shorts = magazine_maker._short_paragraphs(magazine)

    assert [item["length"] for item in shorts] == [240, 220]


def test_section_thumbnail_query_uses_paragraph_image_keyword_before_heading():
    section = {
        "heading": "김치찌개의 현대적 변형",
        "paragraphs": [
            {"image_search_keyword": "kimchi stew pot"},
            {"image_search_keyword": "korean tofu stew"},
        ],
    }

    query = magazine_maker._section_thumbnail_query("김치찌개", section)

    assert query == "kimchi stew pot"
    assert "photography" not in query
    assert "현대적" not in query


def test_section_thumbnail_sync_prefers_first_paragraph_image():
    magazine = {
        "sections": [
            {
                "heading": "김치찌개의 개념과 역사",
                "thumbnail_url": "https://example.com/unrelated-street.jpg",
                "paragraphs": [
                    {"image_url": "https://example.com/kimchi-stew-bowl.jpg"},
                    {"image_url": "https://example.com/another-food.jpg"},
                ],
            }
        ]
    }

    synced = magazine_maker._sync_section_thumbnails_from_paragraphs(magazine)

    assert synced["sections"][0]["thumbnail_url"] == "https://example.com/kimchi-stew-bowl.jpg"
