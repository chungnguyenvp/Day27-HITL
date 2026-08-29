from models import CustomerProfile
import reasoning
from reasoning import deterministic_reasoning, reason_customer


def test_high_churn_customer_gets_credit_limit_proposal():
    result = deterministic_reasoning(
        CustomerProfile(toi=80_000_000, churn_probability=0.9)
    )
    assert result["proposed_action"] == "increase_credit_limit"
    assert result["confidence_score"] == 0.96
    assert "churn" in result["reasoning"].lower()


def test_reason_customer_without_openai_is_local_and_valid():
    result = reason_customer(
        CustomerProfile(toi=250_000_000, churn_probability=0.2),
        use_openai=False,
    )
    assert result["proposed_action"] == "send_email"
    assert 0.0 <= result["confidence_score"] <= 1.0
    assert result["reasoning"]


def test_reason_customer_honors_use_openai_environment_flag(monkeypatch):
    monkeypatch.setenv("USE_OPENAI", "true")
    expected = {
        "proposed_action": "send_email",
        "confidence_score": 0.88,
        "reasoning": "provider result",
    }
    monkeypatch.setattr(reasoning, "_openai_reasoning", lambda customer: expected)

    assert reason_customer(
        CustomerProfile(toi=250_000_000, churn_probability=0.2), use_openai=None
    ) == expected
