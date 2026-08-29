import pytest

from audit import AuditLogError, append_audit_entry, read_audit_entries
from models import AuditEntry


def make_entry(action: str) -> AuditEntry:
    return AuditEntry(
        timestamp="2026-08-29T09:00:00+00:00",
        agent_id="agent",
        action=action,
        confidence=0.9,
        reviewer_id="system",
        decision="auto_execute",
    )


def test_append_preserves_existing_entries(tmp_path):
    path = tmp_path / "audit.json"
    append_audit_entry(make_entry("send_email"), path)
    append_audit_entry(make_entry("increase_credit_limit"), path)
    assert [entry.action for entry in read_audit_entries(path)] == [
        "send_email",
        "increase_credit_limit",
    ]


def test_malformed_audit_file_raises_without_erasing_bytes(tmp_path):
    path = tmp_path / "audit.json"
    path.write_text("{bad", encoding="utf-8")
    with pytest.raises(AuditLogError):
        append_audit_entry(make_entry("send_email"), path)
    assert path.read_text(encoding="utf-8") == "{bad"


def test_read_missing_audit_file_returns_empty_list(tmp_path):
    assert read_audit_entries(tmp_path / "missing.json") == []
