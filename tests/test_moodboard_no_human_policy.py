from app.core import moodboard_maker


def test_no_human_negative_prompt_contains_body_terms():
    negative_prompt = moodboard_maker.build_no_human_negative_prompt()

    for term in [
        "no people",
        "no humans",
        "no person",
        "no face",
        "no portrait",
        "no hands",
        "no arms",
        "no legs",
        "no feet",
        "no body",
        "no mannequin",
    ]:
        assert term in negative_prompt

    for term in [
        "no logos",
        "no text",
        "no labels",
        "no brand marks",
        "no typography",
        "single product shot",
    ]:
        assert term in negative_prompt


def test_prompt_uses_supplied_magazine_keywords_without_category_palette(monkeypatch):
    monkeypatch.setattr(
        moodboard_maker.llm_client,
        "generate_text",
        lambda *args, **kwargs: "premium editorial moodboard with golf glove and grass texture",
    )

    prompt = moodboard_maker.generate_moodboard_prompt(
        topic="골프웨어",
        magazine_tags=["golf glove", "green grass texture", "folded polo fabric"],
    )

    assert "source constraint" in prompt
    assert "golf glove" in prompt
    assert "green grass texture" in prompt
    assert "folded polo fabric" in prompt
    assert "club head detail" not in prompt
    assert "golf balls" not in prompt
    assert "one clear hero object" in prompt
    assert "not a single product shot" in prompt
    assert "no logos" in prompt
    assert "no text" in prompt
    assert "no people" in prompt
    assert "no model" in prompt


def test_general_prompt_uses_keyword_driven_constraints(monkeypatch):
    monkeypatch.setattr(
        moodboard_maker.llm_client,
        "generate_text",
        lambda *args, **kwargs: "premium fashion moodboard with folded linen and color swatches",
    )

    prompt = moodboard_maker.generate_moodboard_prompt(topic="봄 패션", magazine_tags=["FASHION"])

    assert "source constraint" in prompt
    assert "premium editorial cover background" in prompt


def test_moodboard_prompt_does_not_use_object_specific_rejection(monkeypatch):
    monkeypatch.setattr(
        moodboard_maker.llm_client,
        "generate_text",
        lambda *args, **kwargs: "cinema moodboard with perfume bottles and lipstick tubes",
    )

    prompt = moodboard_maker.generate_moodboard_prompt(topic="영화", magazine_tags=["MOVIE"])

    assert prompt != "IRRELEVANT_PROMPT"
    assert "source constraint" in prompt
    assert "no single product shot" in prompt


def test_home_office_prompt_uses_interior_object_palette(monkeypatch):
    monkeypatch.setattr(
        moodboard_maker.llm_client,
        "generate_text",
        lambda *args, **kwargs: "home office productivity setup moodboard",
    )

    prompt = moodboard_maker.generate_moodboard_prompt(topic="홈 오피스 생산성 셋업")

    assert "source constraint" in prompt
    assert "premium editorial cover background" in prompt
    assert "no humans" in prompt


def test_topic_moodboard_source_constraint_does_not_leak_user_interests(monkeypatch):
    monkeypatch.setattr(
        moodboard_maker.llm_client,
        "generate_text",
        lambda *args, **kwargs: "kimchi stew editorial ingredient board",
    )

    prompt = moodboard_maker.generate_moodboard_prompt(
        topic="김치찌개",
        user_interests=["fashion", "movie", "instagram"],
    )

    assert "fashion" not in prompt
    assert "movie" not in prompt
    assert "instagram" not in prompt
    assert "kimchi stew editorial ingredient board" in prompt


def test_visual_elements_keep_topic_keywords_without_weak_terms():
    visual_elements = moodboard_maker.select_visual_elements(
        topic="my",
        magazine_tags=[
            "캡스톤 디자인 전시회 현장 리포트",
            "전시 부스와 시연 영상",
            "printed circuit board prototype",
        ],
        magazine_titles=["my", "캡스톤 디자인 전시회"],
    )

    assert "my" not in visual_elements["keywords"]
    assert "캡스톤 디자인 전시회 현장 리포트" in visual_elements["keywords"]
    assert "전시 부스와 시연 영상" in visual_elements["keywords"]
    assert "printed circuit board prototype" in visual_elements["keywords"]
    assert "translate if needed" in visual_elements["elements"]


def test_prompt_uses_section_headings_and_content_keywords(monkeypatch):
    captured = {}

    def fake_generate_text(system_prompt, user_prompt, *args, **kwargs):
        captured["system"] = system_prompt
        captured["user"] = user_prompt
        return "editorial board with ceramic tumbler, refill station, steel texture"

    monkeypatch.setattr(moodboard_maker.llm_client, "generate_text", fake_generate_text)

    prompt = moodboard_maker.generate_moodboard_prompt(
        topic="친환경 텀블러",
        user_mood="calm",
        magazine_tags=["LIFESTYLE"],
        section_headings=["버려지지 않는 컵의 조건"],
        content_keywords=["스테인리스 텀블러", "리필 스테이션", "세척 루틴"],
    )

    assert "버려지지 않는 컵의 조건" in captured["user"]
    assert "스테인리스 텀블러" in captured["user"]
    assert "리필 스테이션" in captured["system"]
    assert "Magazine section headings and article content keywords are stronger" in captured["system"]
    assert "stainless steel reusable tumbler" in prompt
    assert "bamboo bottle cleaning brush" in prompt
    assert "스테인리스 텀블러" not in prompt


def test_moodboard_prompt_adds_topic_specific_anchor_objects(monkeypatch):
    monkeypatch.setattr(
        moodboard_maker.llm_client,
        "generate_text",
        lambda *args, **kwargs: "premium editorial board with clean materials",
    )

    prompt = moodboard_maker.generate_moodboard_prompt(
        topic="퇴근 후 20분 홈트 루틴",
        content_keywords=["요가 매트", "저항 밴드", "폼롤러"],
    )

    assert "yoga mat" in prompt
    assert "resistance bands" in prompt
    assert "foam roller" in prompt
    assert prompt.index("yoga mat") < prompt.index("premium editorial cover background")


def test_moodboard_prompt_is_compact_and_topic_first(monkeypatch):
    monkeypatch.setattr(
        moodboard_maker.llm_client,
        "generate_text",
        lambda *args, **kwargs: (
            "portable espresso grinder, ceramic demitasse cup, roasted coffee beans, "
            "linen cafe napkin, walnut tray, color palette cards, cinematic light, premium editorial"
        ),
    )

    prompt = moodboard_maker.generate_moodboard_prompt(
        topic="집에서 즐기는 핸드드립 커피",
        content_keywords=["원두 분쇄", "드리퍼", "홈카페"],
    )

    assert prompt.startswith("portable espresso grinder")
    assert "ceramic demitasse cup" in prompt
    assert "premium editorial cover background" in prompt
    assert len(prompt.split()) < 95


def test_generic_routine_word_does_not_trigger_workout_anchors(monkeypatch):
    monkeypatch.setattr(
        moodboard_maker.llm_client,
        "generate_text",
        lambda *args, **kwargs: (
            "terracotta plant pot, brass watering can, moisture meter, pruning shears, "
            "leaf mister bottle, soil sample"
        ),
    )

    prompt = moodboard_maker.generate_moodboard_prompt(topic="초보자를 위한 반려식물 물주기 루틴")

    assert prompt.startswith("terracotta plant pot")
    assert "brass watering can" in prompt
    assert "yoga mat" not in prompt
    assert "hex dumbbells" not in prompt


def test_fallback_url_only_result_is_not_success(monkeypatch):
    monkeypatch.setattr(
        moodboard_maker,
        "generate_moodboard_prompt",
        lambda *args, **kwargs: "object moodboard, no people",
    )
    monkeypatch.setattr(
        moodboard_maker.local_diffusion_client,
        "generate_image",
        lambda *args, **kwargs: None,
    )

    result = moodboard_maker.generate_moodboard(topic="홈 오피스")

    assert result["success"] is False
    assert result["image_url"] is None
    assert result["fallback_url"] is None
    assert result["status"] == "FAILED"


def test_moodboard_generation_defaults(monkeypatch, capsys):
    monkeypatch.delenv("MOODBOARD_WIDTH", raising=False)
    monkeypatch.delenv("MOODBOARD_HEIGHT", raising=False)
    monkeypatch.delenv("MOODBOARD_STEPS", raising=False)
    monkeypatch.delenv("MOODBOARD_GUIDANCE_SCALE", raising=False)
    monkeypatch.setattr(
        moodboard_maker,
        "generate_moodboard_prompt",
        lambda *args, **kwargs: "object moodboard, no people",
    )

    calls = {}

    def fake_generate_image(prompt, **kwargs):
        calls["prompt"] = prompt
        calls.update(kwargs)
        return "data:image/jpeg;base64,abc"

    monkeypatch.setattr(moodboard_maker.local_diffusion_client, "generate_image", fake_generate_image)
    monkeypatch.setattr(
        moodboard_maker.local_diffusion_client,
        "last_timing",
        {
            "inference_steps": 12,
            "image_width": 768,
            "image_height": 768,
            "guidance_scale": 6.0,
            "negative_prompt_applied": True,
        },
    )

    result = moodboard_maker.generate_moodboard(topic="골프웨어", request_id="test-moodboard-policy")
    output = capsys.readouterr().out

    assert result["image_url"].startswith("data:image/jpeg;base64,")
    assert result["status"] == "COMPLETED"
    assert result["success"] is True
    assert calls["width"] == 768
    assert calls["height"] == 768
    assert calls["num_inference_steps"] == 12
    assert calls["guidance_scale"] == 6.0
    assert calls["quality"] == 88
    assert "no people" in calls["negative_prompt"]
    assert "no_human=true" in output
    assert "inference_steps=12" in output


def test_compact_prompt_adds_cover_depth_and_layering(monkeypatch):
    monkeypatch.setattr(
        moodboard_maker.llm_client,
        "generate_text",
        lambda *args, **kwargs: "stainless steel reusable tumbler, cork coaster, refill bottle",
    )

    prompt = moodboard_maker.generate_moodboard_prompt(topic="환경친화 텀블러 추천")

    assert "premium editorial cover background" in prompt
    assert "layered still-life composition" in prompt
    assert "one clear hero object" in prompt
    assert "refined negative space for app title overlay" in prompt
    assert "subtle shadows" in prompt
    assert "cohesive color story" in prompt
    assert "high-end design magazine styling" in prompt
    assert "no paper flatlay grid" in prompt


def test_cherry_blossom_prompt_uses_seasonal_place_anchors(monkeypatch):
    monkeypatch.setattr(
        moodboard_maker.llm_client,
        "generate_text",
        lambda *args, **kwargs: (
            "material layers frosted glass dome over the vase, linen table runner, oak surface base, "
            "blush pink, sage green"
        ),
    )

    prompt = moodboard_maker.generate_moodboard_prompt(
        topic="벚꽃 명소",
        magazine_tags=[
            "벚꽃 명소 올해는 미리 계획해야 합니다 국내 여행 추천 BEST 9",
            "벚꽃 보러 어디 갈까 전국 벚꽃 명소 축제 일정은",
        ],
    )

    assert prompt.startswith("cherry blossom branches")
    assert "soft pink petals" in prompt
    assert "stone park path texture" in prompt
    assert "frosted glass dome" not in prompt
    assert "vase" not in prompt
    assert "BEST 9" not in prompt
    assert "source constraint: BEST" not in prompt


def test_generic_anchored_topic_ignores_unrelated_llm_objects(monkeypatch):
    monkeypatch.setattr(
        moodboard_maker.llm_client,
        "generate_text",
        lambda *args, **kwargs: (
            "perfume bottle, lipstick tube, glass dome, oak tray, generic luxury objects"
        ),
    )

    prompt = moodboard_maker.generate_moodboard_prompt(
        topic="AI 노트북 생산성 도구",
        magazine_tags=["TOP 10 productivity guide", "AI software setup"],
    )

    assert prompt.startswith("minimal device corner")
    assert "glass screen reflection" in prompt
    assert "brushed metal texture" in prompt
    assert "perfume bottle" not in prompt
    assert "lipstick tube" not in prompt
    assert "TOP 10" not in prompt


def test_source_keyword_filter_removes_ranking_noise_generally():
    keywords = moodboard_maker._source_keyword_phrases(
        [
            "국내 여행 추천 BEST 9",
            "TOP 10 productivity guide",
            "봄 재킷 소재와 컬러 팔레트",
            "minimal device corner",
        ]
    )

    assert "국내 여행 추천 BEST 9" not in keywords
    assert "TOP 10 productivity guide" not in keywords
    assert "봄 재킷 소재와 컬러 팔레트" in keywords
    assert "minimal device corner" in keywords
