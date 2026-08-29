from pydantic import ValidationError
import pytest

from models import AuditEntry, CustomerProfile


def test_customer_profile_rejects_probability_outside_unit_interval():
    with pytest.raises(ValidationError):
        CustomerProfile(toi=1_000_000, churn_probability=1.1)


def test_audit_entry_round_trips_required_fields():
    entry = AuditEntry(
        timestamp="2026-08-29T09:00:00+00:00",
        agent_id="churn-risk-agent",
        action="send_email",
        confidence=0.9,
        reviewer_id="system",
        decision="auto_execute",
    )
    assert entry.confidence == 0.9
    assert entry.model_dump()["decision"] == "auto_execute"
