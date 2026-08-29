import pytest

from app import normalize_decision, openai_enabled_by_default


def test_normalize_decision_requires_edit_value_for_edit():
    with pytest.raises(ValueError, match="edited_action"):
        normalize_decision("Edit", None)


def test_normalize_decision_returns_lowercase_contract():
    assert normalize_decision("Approve", None) == ("approve", None)


def test_normalize_decision_rejects_unknown_button_value():
    with pytest.raises(ValueError, match="decision"):
        normalize_decision("Escalate", None)


def test_openai_toggle_defaults_from_environment(monkeypatch):
    monkeypatch.setenv("USE_OPENAI", "true")
    assert openai_enabled_by_default() is True
