from models import CustomerProfile
import pytest

from audit import read_audit_entries
from graph import build_graph, route_action


def test_credit_limit_is_high_risk_even_at_099():
    assert route_action(
        {"proposed_action": "increase_credit_limit", "confidence_score": 0.99}
    ) == "execute_high_risk_action"


def test_send_email_at_threshold_auto_executes():
    assert route_action(
        {"proposed_action": "send_email", "confidence_score": 0.85}
    ) == "execute_low_risk_action"


def test_send_email_below_threshold_escalates():
    assert route_action(
        {"proposed_action": "send_email", "confidence_score": 0.84}
    ) == "execute_high_risk_action"


def test_unknown_action_is_rejected():
    with pytest.raises(ValueError, match="Unsupported action"):
        route_action({"proposed_action": "wire_money", "confidence_score": 1.0})


def test_high_risk_graph_pauses_before_execution(tmp_path):
    graph = build_graph(audit_path=tmp_path / "audit.json")
    config = {"configurable": {"thread_id": "pause-case"}}
    graph.invoke(
        {
            "customer_id": "CUST-HIGH",
            "customer": CustomerProfile(toi=80_000_000, churn_probability=0.9).model_dump(),
            "human_decision": None,
        },
        config,
    )
    checkpoint = graph.get_state(config)
    assert checkpoint.next == ("execute_high_risk_action",)
    assert checkpoint.values["proposed_action"] == "increase_credit_limit"
    assert "execution_status" not in checkpoint.values


def _run_high_risk_decision(tmp_path, thread_id, **updates):
    graph = build_graph(audit_path=tmp_path / f"{thread_id}.json")
    config = {"configurable": {"thread_id": thread_id}}
    graph.invoke(
        {
            "customer_id": thread_id,
            "customer": CustomerProfile(toi=80_000_000, churn_probability=0.9).model_dump(),
            "human_decision": None,
        },
        config,
    )
    graph.update_state(config, updates)
    return graph.invoke(None, config), graph


def test_approve_resumes_and_executes_action(tmp_path):
    result, _ = _run_high_risk_decision(
        tmp_path, "approve-case", human_decision="approve", reviewer_id="op1"
    )
    assert result["execution_status"] == "executed"
    assert result["execution_message"] == "increase_credit_limit"


def test_reject_resumes_without_executing_action(tmp_path):
    result, _ = _run_high_risk_decision(
        tmp_path, "reject-case", human_decision="reject", reviewer_id="op2"
    )
    assert result["execution_status"] == "rejected"


def test_edit_resumes_with_reviewer_action(tmp_path):
    result, _ = _run_high_risk_decision(
        tmp_path,
        "edit-case",
        human_decision="edit",
        edited_action="send_email",
        reviewer_id="op3",
    )
    assert result["execution_status"] == "executed"
    assert result["execution_message"] == "send_email"


def test_low_risk_graph_auto_executes_and_audits(tmp_path):
    path = tmp_path / "audit.json"
    graph = build_graph(audit_path=path)
    config = {"configurable": {"thread_id": "low-case"}}
    result = graph.invoke(
        {
            "customer_id": "CUST-LOW",
            "customer": CustomerProfile(toi=250_000_000, churn_probability=0.2).model_dump(),
            "human_decision": None,
        },
        config,
    )
    assert result["execution_status"] == "executed"
    entries = read_audit_entries(path)
    assert len(entries) == 1
    assert entries[0].decision == "auto_execute"
