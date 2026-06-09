import sys
from types import SimpleNamespace

sys.modules.setdefault("runpod", SimpleNamespace(serverless=SimpleNamespace(start=lambda *_: None)))

import handler


def test_edit_rejection_uses_business_error_code_not_runpod_error(monkeypatch):
    class Intent:
        action = "add_section"
        instruction = "선크림 추천"
        response_message = "추천 섹션을 추가합니다."
        target_section_index = None

    monkeypatch.setattr("app.core.magazine_editor.analyze_user_intent", lambda *_: Intent())
    monkeypatch.setattr(
        "app.core.magazine_editor.add_new_section",
        lambda *_: {
            "error": "INSUFFICIENT_VERIFIED_SOURCES",
            "success": False,
            "message": "검증 가능한 검색 결과가 없습니다.",
        },
    )

    result = handler.handle_edit_magazine({
        "message": "선크림 추천",
        "magazine_data": {"title": "여름 패션", "sections": []},
    })

    assert result["success"] is False
    assert result["error_code"] == "INSUFFICIENT_VERIFIED_SOURCES"
    assert "error" not in result
    assert result["updated_magazine"]["new_sections"] == []
    assert result["updated_magazine"]["heading"] == "검증 가능한 검색 결과가 없습니다."


def test_regenerate_without_target_handles_add_section_rejection(monkeypatch):
    class Intent:
        action = "regenerate_section"
        instruction = "장소 추천"
        response_message = "섹션을 변경합니다."
        target_section_index = None

    monkeypatch.setattr("app.core.magazine_editor.analyze_user_intent", lambda *_: Intent())
    monkeypatch.setattr(
        "app.core.magazine_editor.add_new_section",
        lambda *_: {
            "error": "INSUFFICIENT_VERIFIED_SOURCES",
            "success": False,
            "message": "검증 가능한 검색 결과가 없습니다.",
        },
    )

    result = handler.handle_edit_magazine({
        "message": "장소 추천",
        "magazine_data": {"title": "여행", "sections": []},
    })

    assert result["intent"] == "add_section"
    assert result["error_code"] == "INSUFFICIENT_VERIFIED_SOURCES"
    assert "error" not in result


def test_edit_exception_does_not_mark_runpod_job_failed(monkeypatch):
    monkeypatch.setattr(
        "app.core.magazine_editor.analyze_user_intent",
        lambda *_: (_ for _ in ()).throw(ValueError("bad response")),
    )

    result = handler.handle_edit_magazine({
        "message": "섹션 추가",
        "magazine_data": {"title": "여행", "sections": []},
    })

    assert result["success"] is False
    assert result["error_code"] == "EDIT_MAGAZINE_FAILED"
    assert "error" not in result
    assert result["updated_magazine"]["new_sections"] == []
