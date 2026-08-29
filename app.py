"""Streamlit approval console for the churn-risk LangGraph workflow."""

from __future__ import annotations

import os
from uuid import uuid4

import streamlit as st

from config import load_environment
from graph import build_graph, new_config
from models import CustomerProfile


load_environment()


CUSTOMER_PRESETS: dict[str, CustomerProfile] = {
    "CUST001 · High churn": CustomerProfile(toi=80_000_000, churn_probability=0.90),
    "CUST002 · Moderate churn": CustomerProfile(
        toi=140_000_000, churn_probability=0.62
    ),
    "CUST003 · Low churn": CustomerProfile(toi=250_000_000, churn_probability=0.20),
}


def normalize_decision(
    decision: str, edited_action: str | None
) -> tuple[str, str | None]:
    normalized = decision.strip().lower()
    if normalized not in {"approve", "reject", "edit"}:
        raise ValueError("decision must be Approve, Reject, or Edit")
    if normalized == "edit":
        action = (edited_action or "").strip()
        if not action:
            raise ValueError("edited_action is required when decision is Edit")
        return normalized, action
    return normalized, None


def start_customer_workflow(graph, customer: CustomerProfile, config: dict) -> dict:
    customer_id = config.get("configurable", {}).get("thread_id", "customer")
    return graph.invoke(
        {
            "customer_id": customer_id,
            "customer": customer.model_dump(),
            "human_decision": None,
        },
        config,
    )


def resume_with_decision(
    graph,
    config: dict,
    decision: str,
    edited_action: str | None = None,
    reviewer_id: str = "operator_01",
) -> dict:
    normalized, action = normalize_decision(decision, edited_action)
    reviewer = reviewer_id.strip()
    if not reviewer:
        raise ValueError("reviewer_id is required")
    updates: dict[str, object] = {
        "human_decision": normalized,
        "reviewer_id": reviewer,
    }
    if action is not None:
        updates["edited_action"] = action
    graph.update_state(config, updates)
    return graph.invoke(None, config)


@st.cache_resource(show_spinner=False)
def _cached_graph(use_openai: bool):
    return build_graph(
        audit_path=os.getenv("AUDIT_LOG_PATH", "audit_log.json"),
        use_openai=use_openai,
    )


def _ensure_session(use_openai: bool) -> None:
    if "workflow_graph" not in st.session_state or st.session_state.get(
        "use_openai"
    ) != use_openai:
        st.session_state.workflow_graph = _cached_graph(use_openai)
        st.session_state.use_openai = use_openai


def render_app() -> None:
    st.set_page_config(page_title="Churn Risk HITL", page_icon="🛡️", layout="wide")
    st.title("🛡️ Churn Risk · Human-in-the-Loop")
    st.caption(
        "Agent đề xuất, policy định tuyến, con người phê duyệt hành động rủi ro cao."
    )

    with st.sidebar:
        st.header("Workflow setup")
        use_openai = st.toggle(
            "Use OpenAI reasoner (optional)",
            value=False,
            help="Requires OPENAI_API_KEY in your local environment; never paste it here.",
        )
        preset_label = st.selectbox("Customer preset", list(CUSTOMER_PRESETS))
        customer_id = st.text_input("Customer ID", value="CUST001")
        reviewer_id = st.text_input("Reviewer ID", value="operator_01")
        start = st.button("▶️ Evaluate customer", type="primary", use_container_width=True)

    _ensure_session(use_openai)
    graph = st.session_state.workflow_graph
    if start:
        customer = CUSTOMER_PRESETS[preset_label]
        config = new_config(f"{customer_id.strip() or 'customer'}-{uuid4().hex[:8]}")
        st.session_state.workflow_config = config
        st.session_state.workflow_customer_id = customer_id.strip() or "customer"
        graph.invoke(
            {
                "customer_id": st.session_state.workflow_customer_id,
                "customer": customer.model_dump(),
                "human_decision": None,
            },
            config,
        )
        st.rerun()

    config = st.session_state.get("workflow_config")
    if not config:
        st.info("Chọn customer và bấm Evaluate customer để bắt đầu.")
        return

    snapshot = graph.get_state(config)
    values = snapshot.values
    st.subheader(f"Customer {values.get('customer_id', 'unknown')}")
    left, middle, right = st.columns(3)
    left.metric("Proposed action", values.get("proposed_action", "—"))
    middle.metric(
        "Confidence",
        f"{float(values.get('confidence_score', 0.0)):.0%}",
    )
    right.metric("Status", values.get("execution_status", "pending review"))
    st.markdown("**Reasoning**")
    st.write(values.get("reasoning", "No reasoning available."))

    pending = "execute_high_risk_action" in (snapshot.next or ())
    if pending:
        st.warning("⏸️ High-risk action is paused until a human reviewer decides.")
        edited_action = st.selectbox(
            "Edited action (used only with Edit)",
            ["send_email", "increase_credit_limit"],
        )
        approve_col, reject_col, edit_col = st.columns(3)
        if approve_col.button("✅ Approve", use_container_width=True):
            resume_with_decision(graph, config, "Approve", reviewer_id=reviewer_id)
            st.rerun()
        if reject_col.button("🛑 Reject", use_container_width=True):
            resume_with_decision(graph, config, "Reject", reviewer_id=reviewer_id)
            st.rerun()
        if edit_col.button("✏️ Edit & apply", use_container_width=True):
            resume_with_decision(
                graph,
                config,
                "Edit",
                edited_action=edited_action,
                reviewer_id=reviewer_id,
            )
            st.rerun()
    elif values.get("execution_status"):
        if values["execution_status"] == "executed":
            st.success(f"Action completed: {values.get('execution_message', '—')}")
        elif values["execution_status"] == "rejected":
            st.error(values.get("execution_message", "Action rejected"))

    st.divider()
    st.caption(
        "Audit trail: "
        f"{os.getenv('AUDIT_LOG_PATH', 'audit_log.json')} · "
        "Confidence threshold: 85% · increase_credit_limit always requires review"
    )


if __name__ == "__main__":
    render_app()
