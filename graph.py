"""LangGraph workflow for churn-risk proposals and human approval."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from audit import append_audit_entry
from models import AuditEntry, CustomerProfile, GraphState
from reasoning import reason_customer


CONFIDENCE_THRESHOLD = 0.85
AGENT_ID = "churn-risk-agent"
LOW_RISK_ACTIONS = {"send_email"}
HIGH_RISK_ACTIONS = {"increase_credit_limit"}
SUPPORTED_ACTIONS = LOW_RISK_ACTIONS | HIGH_RISK_ACTIONS


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _customer_from_state(state: GraphState) -> CustomerProfile:
    customer = state.get("customer")
    if isinstance(customer, CustomerProfile):
        return customer
    if isinstance(customer, dict):
        return CustomerProfile.model_validate(customer)
    raise ValueError("state must include a valid customer profile")


def evaluate_customer(state: GraphState, *, use_openai: bool = False) -> dict[str, object]:
    customer = _customer_from_state(state)
    proposal = reason_customer(customer, use_openai=use_openai)
    return {
        "proposed_action": proposal["proposed_action"],
        "confidence_score": proposal["confidence_score"],
        "reasoning": proposal["reasoning"],
        "agent_id": AGENT_ID,
    }


def route_action(
    state: GraphState,
) -> Literal["execute_low_risk_action", "execute_high_risk_action"]:
    action = state.get("proposed_action")
    confidence = state.get("confidence_score")
    if action not in SUPPORTED_ACTIONS:
        raise ValueError(f"Unsupported action: {action}")
    try:
        confidence_value = float(confidence)
    except (TypeError, ValueError) as exc:
        raise ValueError("confidence_score must be numeric") from exc
    if not 0.0 <= confidence_value <= 1.0:
        raise ValueError("confidence_score must be between 0 and 1")
    # Hard policy has precedence over confidence.
    if action in HIGH_RISK_ACTIONS:
        return "execute_high_risk_action"
    if action in LOW_RISK_ACTIONS and confidence_value >= CONFIDENCE_THRESHOLD:
        return "execute_low_risk_action"
    return "execute_high_risk_action"


def _audit_path(state: GraphState) -> str | Path:
    return state.get("audit_path", "audit_log.json")


def _append_audit(payload: dict[str, object], path: str | Path) -> None:
    append_audit_entry(AuditEntry.model_validate(payload), path)


def execute_low_risk_action(state: GraphState) -> dict[str, object]:
    action = state.get("proposed_action")
    if action not in LOW_RISK_ACTIONS:
        raise ValueError("Only low-risk actions may use the low-risk executor")
    _append_audit(
        {
            "timestamp": _now(),
            "agent_id": state.get("agent_id", AGENT_ID),
            "action": action,
            "confidence": float(state["confidence_score"]),
            "reviewer_id": "system",
            "decision": "auto_execute",
            "customer_id": state.get("customer_id"),
            "metadata": {"reasoning": state.get("reasoning", "")},
        },
        _audit_path(state),
    )
    return {
        "execution_status": "executed",
        "execution_message": action,
        "human_decision": "auto_execute",
    }


def execute_high_risk_action(state: GraphState) -> dict[str, object]:
    decision = (state.get("human_decision") or "").strip().lower()
    proposed_action = state.get("proposed_action")
    if proposed_action not in SUPPORTED_ACTIONS:
        raise ValueError(f"Unsupported action: {proposed_action}")
    reviewer_id = (state.get("reviewer_id") or "").strip()
    if decision not in {"approve", "reject", "edit"}:
        return {
            "execution_status": "pending_review",
            "execution_message": "A human decision is required before execution.",
        }
    final_action = proposed_action
    if decision == "edit":
        final_action = (state.get("edited_action") or "").strip()
        if final_action not in SUPPORTED_ACTIONS:
            raise ValueError("edited_action must be a supported action")
    if not reviewer_id:
        raise ValueError("reviewer_id is required for a human decision")
    status = "rejected" if decision == "reject" else "executed"
    message = "Action rejected by reviewer" if decision == "reject" else final_action
    _append_audit(
        {
            "timestamp": _now(),
            "agent_id": state.get("agent_id", AGENT_ID),
            "action": final_action if decision != "reject" else proposed_action,
            "confidence": float(state["confidence_score"]),
            "reviewer_id": reviewer_id,
            "decision": decision,
            "customer_id": state.get("customer_id"),
            "metadata": {
                "original_action": proposed_action,
                "reasoning": state.get("reasoning", ""),
            },
        },
        _audit_path(state),
    )
    return {
        "execution_status": status,
        "execution_message": message,
    }


def build_graph(
    audit_path: str | Path = "audit_log.json", use_openai: bool = False
):
    """Compile a checkpointed graph that pauses before high-risk execution."""

    builder = StateGraph(GraphState)
    audit_path_string = str(audit_path)
    builder.add_node(
        "evaluate_customer",
        lambda state: {
            **evaluate_customer(state, use_openai=use_openai),
            "audit_path": state.get("audit_path", audit_path_string),
        },
    )
    builder.add_node(
        "execute_low_risk_action",
        lambda state: execute_low_risk_action(state),
    )
    builder.add_node(
        "execute_high_risk_action",
        lambda state: execute_high_risk_action(state),
    )
    builder.add_edge(START, "evaluate_customer")
    builder.add_conditional_edges(
        "evaluate_customer",
        route_action,
        {
            "execute_low_risk_action": "execute_low_risk_action",
            "execute_high_risk_action": "execute_high_risk_action",
        },
    )
    builder.add_edge("execute_low_risk_action", END)
    builder.add_edge("execute_high_risk_action", END)
    return builder.compile(
        checkpointer=MemorySaver(),
        interrupt_before=["execute_high_risk_action"],
    )


def new_config(thread_id: str) -> dict[str, dict[str, str]]:
    if not thread_id.strip():
        raise ValueError("thread_id must not be blank")
    return {"configurable": {"thread_id": thread_id}}
