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


def test_golfwear_prompt_uses_product_object_material_palette(monkeypatch):
    monkeypatch.setattr(
        moodboard_maker.llm_client,
        "generate_text",
        lambda *args, **kwargs: "premium golfwear moodboard",
    )

    prompt = moodboard_maker.generate_moodboard_prompt(topic="골프웨어", magazine_tags=["FASHION", "SPORTS"])

    assert "golf gloves" in prompt
    assert "golf balls" in prompt
    assert "premium textile swatches" in prompt
    assert "folded polo fabric swatch" in prompt
    assert "club head detail" in prompt
    assert "color palette cards" in prompt
    assert "stitching detail" in prompt
    assert "multiple curated objects" in prompt
    assert "not a single product shot" in prompt
    assert "no logos" in prompt
    assert "no text" in prompt
    assert "no people" in prompt
    assert "no model" in prompt


def test_home_office_prompt_uses_interior_object_palette(monkeypatch):
    monkeypatch.setattr(
        moodboard_maker.llm_client,
        "generate_text",
        lambda *args, **kwargs: "home office productivity setup moodboard",
    )

    prompt = moodboard_maker.generate_moodboard_prompt(topic="홈 오피스 생산성 셋업")

    assert "desk lamp" in prompt
    assert "keyboard" in prompt
    assert "ergonomic chair detail" in prompt
    assert "no humans" in prompt


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
            "inference_steps": 8,
            "image_width": 768,
            "image_height": 768,
            "guidance_scale": 5.0,
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
    assert calls["num_inference_steps"] == 8
    assert calls["guidance_scale"] == 5.0
    assert "no people" in calls["negative_prompt"]
    assert "no_human=true" in output
    assert "inference_steps=8" in output
