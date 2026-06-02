from app.core import magazine_maker
from app.core import moodboard_maker
from app.core import searcher


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
    monkeypatch.setattr(
        magazine_maker,
        "search_with_pexels_metadata",
        lambda *args, **kwargs: [
            {
                "id": 1,
                "url": "https://images.pexels.com/photos/1/pexels-photo-1.jpeg?w=1200",
                "width": 1200,
                "height": 800,
                "dedupe_key": "pexels:1",
            }
        ],
    )
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


def test_user_mood_is_not_in_magazine_body_prompt(monkeypatch):
    captured = {}

    class CapturingLLM(MockLLM):
        def generate_json(self, system_prompt, user_prompt, **kwargs):
            captured["system"] = system_prompt
            captured["user"] = user_prompt
            return super().generate_json(system_prompt, user_prompt, **kwargs)

    monkeypatch.setattr(magazine_maker, "llm_client", CapturingLLM(_valid_magazine_json()))
    monkeypatch.setattr(
        magazine_maker,
        "search_with_tavily",
        lambda *args, **kwargs: (
            [{"url": "https://example.com/a", "content": "a"}],
            ["https://example.com/cover.jpg"],
        ),
    )
    monkeypatch.setattr(
        magazine_maker,
        "scrape_labeled_sources",
        lambda *args, **kwargs: ([("https://example.com/a", "a")], []),
    )
    monkeypatch.setattr(magazine_maker, "validate_image_url", lambda url: True)
    monkeypatch.setattr(magazine_maker, "search_with_pexels_metadata", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        moodboard_maker,
        "generate_moodboard",
        lambda **kwargs: {
            "image_url": "https://example.com/moodboard.png",
            "description": "premium editorial moodboard",
            "success": True,
        },
    )

    magazine_maker.generate_magazine_content(
        "홈 오피스",
        user_interests=["인테리어"],
        user_mood="몽환적이고 우울한 톤",
        request_id="test-user-mood-split",
    )

    assert "몽환적이고 우울한 톤" not in captured["system"]
    assert "몽환적이고 우울한 톤" not in captured["user"]


def test_create_magazine_returns_contract_when_moodboard_fails(monkeypatch):
    monkeypatch.setattr(magazine_maker, "llm_client", MockLLM(_valid_magazine_json()))
    monkeypatch.setattr(
        magazine_maker,
        "search_with_tavily",
        lambda *args, **kwargs: (
            [{"url": "https://example.com/a", "content": "a"}],
            [],
        ),
    )
    monkeypatch.setattr(
        magazine_maker,
        "scrape_labeled_sources",
        lambda *args, **kwargs: ([("https://example.com/a", "a")], []),
    )
    monkeypatch.setattr(magazine_maker, "validate_image_url", lambda url: True)
    monkeypatch.setattr(magazine_maker, "search_with_pexels_metadata", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        moodboard_maker,
        "generate_moodboard",
        lambda **kwargs: {
            "image_url": None,
            "description": "",
            "success": False,
            "status": "FAILED",
            "error_type": "IMAGE_GENERATION_FAILED",
            "fallback_url": None,
        },
    )

    result = magazine_maker.generate_magazine_content("홈 오피스", request_id="test-moodboard-fail")

    assert result["success"] is False
    assert result["error_type"] == "IMAGE_GENERATION_FAILED"
    assert result["moodboard"]["image_url"] is None
    assert result["moodboard"]["description"] == ""
    assert len(result["sections"]) == 2
    for section in result["sections"]:
        assert "heading" in section
        assert "thumbnail_url" in section
        assert len(section["paragraphs"]) == 3
        for para in section["paragraphs"]:
            assert set(["subtitle", "text", "image_url", "source_url"]).issubset(para)


def test_create_magazine_records_image_future_errors_without_500(monkeypatch, capsys):
    monkeypatch.setattr(magazine_maker, "llm_client", MockLLM(_valid_magazine_json()))
    monkeypatch.setattr(
        magazine_maker,
        "search_with_tavily",
        lambda *args, **kwargs: (
            [{"url": "https://example.com/a", "content": "a"}],
            [],
        ),
    )
    monkeypatch.setattr(
        magazine_maker,
        "scrape_labeled_sources",
        lambda *args, **kwargs: ([("https://example.com/a", "a")], []),
    )
    monkeypatch.setattr(magazine_maker, "validate_image_url", lambda url: True)

    def fail_pexels(*args, **kwargs):
        raise RuntimeError("pexels unavailable")

    monkeypatch.setattr(magazine_maker, "search_with_pexels_metadata", fail_pexels)
    monkeypatch.setattr(
        moodboard_maker,
        "generate_moodboard",
        lambda **kwargs: {
            "image_url": "https://example.com/moodboard.png",
            "description": "premium editorial moodboard",
            "success": True,
        },
    )

    result = magazine_maker.generate_magazine_content("홈 오피스", request_id="test-image-future-error")
    output = capsys.readouterr().out

    assert result["moodboard"]["image_url"] == "https://example.com/moodboard.png"
    assert len(result["sections"]) == 2
    assert "Pexels search failed" in output


def test_magazine_plan_defaults_fill_missing_fields():
    plan = magazine_maker._normalize_magazine_plan({"tags": ["UNKNOWN"], "section_headings": []}, "친환경 텀블러")

    assert plan["title"] == "친환경 텀블러 매거진"
    assert plan["tags"]
    assert all(tag in magazine_maker.ALLOWED_MAGAZINE_TAGS for tag in plan["tags"])
    assert len(plan["section_headings"]) == 2
    assert plan["visual_keywords"]
    assert plan["moodboard_subjects"]
    assert "fallback placeholder" in plan["forbidden_visuals"]


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


def test_educational_section_headings_are_sanitized():
    magazine = _valid_magazine_json()
    magazine["sections"][0]["heading"] = "개념"
    magazine["sections"][1]["heading"] = "환경 이점"
    magazine["sections"][0]["paragraphs"][0]["subtitle"] = "활용법"

    normalized = magazine_maker._normalize_magazine_contract(magazine, "환경친화 텀블러 추천")

    headings = [section["heading"] for section in normalized["sections"]]
    assert headings == ["매일 들고 나가는 온도", "버려지지 않는 컵의 조건"]
    assert normalized["sections"][0]["paragraphs"][0]["subtitle"] == "매일 들고 나가는 온도의 장면 1"
    assert all(not magazine_maker._looks_educational_title(heading) for heading in headings)


def test_fill_missing_final_images_keeps_empty_paragraphs_null():
    magazine = _valid_magazine_json()
    magazine["cover_image_url"] = "https://example.com/cover.jpg"
    magazine["sections"][0]["paragraphs"][0]["image_url"] = None
    magazine["sections"][1]["paragraphs"][0]["image_url"] = None

    filled = magazine_maker._fill_missing_final_images(magazine, magazine["cover_image_url"])

    assert filled["sections"][0]["paragraphs"][0]["image_url"] is None
    assert filled["sections"][1]["paragraphs"][0]["image_url"] is None


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

    synced = magazine_maker._sync_section_thumbnails_from_paragraphs(magazine, overwrite=True)

    assert synced["sections"][0]["thumbnail_url"] == "https://example.com/kimchi-stew-bowl.jpg"


def test_topic_thumbnail_query_translates_to_exact_visual_subject(monkeypatch):
    monkeypatch.setattr(
        magazine_maker.llm_client,
        "generate_text",
        lambda *args, **kwargs: "kimchi stew bowl",
    )

    query = magazine_maker._topic_thumbnail_query("김치찌개")

    assert query == "kimchi stew bowl"


def test_section_thumbnail_sync_keeps_exact_topic_thumbnail_unless_missing():
    magazine = {
        "sections": [
            {
                "thumbnail_url": "https://example.com/exact-kimchi-stew.jpg",
                "paragraphs": [{"image_url": "https://example.com/related-kimchi-rice.jpg"}],
            }
        ]
    }

    synced = magazine_maker._sync_section_thumbnails_from_paragraphs(magazine)

    assert synced["sections"][0]["thumbnail_url"] == "https://example.com/exact-kimchi-stew.jpg"


def test_pexels_same_photo_id_has_one_dedupe_key():
    first = {"id": 123, "url": "https://images.pexels.com/photos/123/a.jpeg?w=150"}
    second = {"id": 123, "url": "https://images.pexels.com/photos/123/a.jpeg?w=1200"}

    assert magazine_maker._image_dedupe_key(first) == "pexels:123"
    assert magazine_maker._image_dedupe_key(first) == magazine_maker._image_dedupe_key(second)


def test_same_pexels_path_with_different_query_string_is_duplicate():
    first = "https://images.pexels.com/photos/123/a.jpeg?w=150&auto=compress"
    second = "https://images.pexels.com/photos/123/a.jpeg?w=1200"

    assert magazine_maker._image_dedupe_key(first) == magazine_maker._image_dedupe_key(second)


def test_low_resolution_url_is_excluded_by_policy():
    assert magazine_maker._is_low_resolution_url("https://images.pexels.com/photos/1/a.jpeg?w=150") is True
    assert magazine_maker._is_low_resolution_url("https://images.pexels.com/photos/1/a.jpeg?w=940&h=500") is True
    assert magazine_maker._is_low_resolution_url("https://images.pexels.com/photos/1/tiny/a.jpeg") is True
    assert magazine_maker._is_low_resolution_url("https://images.pexels.com/photos/1/a.jpeg?w=1200") is False
    assert magazine_maker._is_low_resolution_url("https://images.pexels.com/photos/1/a.jpeg?w=940&h=650") is False
    assert magazine_maker._is_low_resolution_url("https://images.pexels.com/photos/1/a.jpeg?auto=compress&cs=tinysrgb&w=1260") is False


def test_pexels_metadata_filters_low_resolution_and_prefers_large2x():
    low = {"id": 1, "width": 800, "height": 600, "src": {"large2x": "https://example.com/low.jpg"}}
    high = {
        "id": 2,
        "width": 1200,
        "height": 800,
        "alt": "desk",
        "photographer": "A",
        "src": {
            "large": "https://example.com/large.jpg",
            "large2x": "https://example.com/large2x.jpg",
            "original": "https://example.com/original.jpg",
        },
    }

    assert searcher._pexels_photo_to_metadata(low) == {}
    metadata = searcher._pexels_photo_to_metadata(high)
    assert metadata["url"] == "https://example.com/large2x.jpg"
    assert metadata["dedupe_key"] == "pexels:2"


def test_dedupe_and_pad_paragraph_texts_removes_duplicate_short_text():
    magazine = _valid_magazine_json()
    duplicate = "짧은 문단입니다."
    magazine["sections"][1]["paragraphs"][1]["text"] = duplicate
    magazine["sections"][1]["paragraphs"][2]["text"] = duplicate

    fixed = magazine_maker._dedupe_and_pad_paragraph_texts(magazine, "홈트 루틴")

    first = fixed["sections"][1]["paragraphs"][1]["text"]
    second = fixed["sections"][1]["paragraphs"][2]["text"]
    assert first != second
    assert magazine_maker._paragraph_length(first) >= magazine_maker.PARAGRAPH_MIN_CHARS
    assert magazine_maker._paragraph_length(second) >= magazine_maker.PARAGRAPH_MIN_CHARS


def test_ensure_minimum_unique_images_fills_content_slots_with_pexels(monkeypatch):
    magazine = _valid_magazine_json()
    candidates = [
        {
            "id": 100 + index,
            "url": f"https://images.pexels.com/photos/{100 + index}/image.jpeg?auto=compress&cs=tinysrgb&w=1260",
            "width": 1260,
            "height": 840,
            "dedupe_key": f"pexels:{100 + index}",
        }
        for index in range(8)
    ]

    monkeypatch.setattr(magazine_maker, "search_with_pexels_metadata", lambda *args, **kwargs: candidates)

    used = set()
    fixed = magazine_maker._ensure_minimum_unique_images(
        magazine,
        "홈 오피스",
        used,
        min_images=magazine_maker._count_content_image_slots(magazine),
    )

    assert magazine_maker._count_content_images(fixed) == magazine_maker._count_content_image_slots(fixed)
    urls = [target[field] for target, field in magazine_maker._iter_image_slots(fixed)]
    assert len(urls) == len(set(urls))
