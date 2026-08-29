# Churn Risk HITL Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline execution selected by the user) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a runnable, test-covered LangGraph churn-risk workflow with deterministic reasoning, optional OpenAI reasoning, Streamlit human approval, and append-only audit logging.

**Architecture:** Keep domain models, audit persistence, reasoning providers, graph construction, and Streamlit presentation in focused modules. The graph uses `MemorySaver` and interrupts before high-risk execution; the UI updates and resumes the same checkpoint thread.

**Tech Stack:** Python 3.10+, LangGraph, LangChain, Streamlit, Pydantic v2, optional official OpenAI Python SDK, pytest.

**Spec:** `docs/superpowers/specs/2026-08-29-churn-hitl-design.md`

## Global Constraints

- Default execution must be deterministic and require no network or API key.
- `increase_credit_limit` always requires human review, regardless of confidence.
- Low-risk actions auto-execute only when confidence is >= 0.85.
- High-risk execution is compiled with `interrupt_before=["execute_high_risk_action"]`.
- Never store, print, test-fixture, or commit an API key or real `.env` credential.
- Audit history must be append-only from the caller's perspective and preserve prior entries.

### Task 1: Project scaffold and validated domain models

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `models.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Produces `CustomerProfile(toi: float, churn_probability: float, segment: str = "standard")`.
- Produces `GraphState` with required lab keys and optional `customer`, `reviewer_id`, `edited_action`, `execution_status`, `execution_message`, `audit_path`.
- Produces `AuditEntry(timestamp, agent_id, action, confidence, reviewer_id, decision, customer_id=None, metadata={})`.

- [ ] **Step 1: Write failing schema tests**

```python
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
```

- [ ] **Step 2: Run `py -3.13 -m pytest tests/test_models.py -q`; verify it fails because `models` is missing.**
- [ ] **Step 3: Implement the Pydantic models, TypedDict, confidence bounds, and decision/action literals.**
- [ ] **Step 4: Run the same test; verify both tests pass.**
- [ ] **Step 5: Add dependency pins and ignore `.venv/`, `__pycache__/`, `.pytest_cache/`, `.env`, and `audit_log.json`; commit `feat: add validated HITL domain models`.**

### Task 2: Atomic append-only audit repository

**Files:**
- Create: `audit.py`
- Create: `tests/test_audit.py`

**Interfaces:**
- `read_audit_entries(path: str | Path = "audit_log.json") -> list[AuditEntry]`.
- `append_audit_entry(entry: AuditEntry, path: str | Path = "audit_log.json") -> AuditEntry`.
- `AuditLogError` for malformed/non-list JSON or unrecoverable I/O.

- [ ] **Step 1: Write failing tests for creating, appending, and rejecting malformed logs.**

```python
import json
import pytest
from audit import AuditLogError, append_audit_entry, read_audit_entries
from models import AuditEntry

def make_entry(action: str) -> AuditEntry:
    return AuditEntry(timestamp="2026-08-29T09:00:00+00:00", agent_id="agent", action=action, confidence=0.9, reviewer_id="system", decision="auto_execute")

def test_append_preserves_existing_entries(tmp_path):
    path = tmp_path / "audit.json"
    append_audit_entry(make_entry("send_email"), path)
    append_audit_entry(make_entry("increase_credit_limit"), path)
    assert [e.action for e in read_audit_entries(path)] == ["send_email", "increase_credit_limit"]

def test_malformed_audit_file_raises_without_erasing_bytes(tmp_path):
    path = tmp_path / "audit.json"
    path.write_text("{bad", encoding="utf-8")
    with pytest.raises(AuditLogError):
        append_audit_entry(make_entry("send_email"), path)
    assert path.read_text(encoding="utf-8") == "{bad"
```

- [ ] **Step 2: Run `py -3.13 -m pytest tests/test_audit.py -q`; verify the expected missing-module failure.**
- [ ] **Step 3: Implement JSON list loading, Pydantic validation, same-directory temp-file write, `os.replace`, and clear errors.**
- [ ] **Step 4: Run the audit tests; verify they pass.**
- [ ] **Step 5: Commit `feat: add atomic append-only audit log`.**

### Task 3: Deterministic and optional OpenAI reasoning

**Files:**
- Create: `reasoning.py`
- Create: `tests/test_reasoning.py`

**Interfaces:**
- `deterministic_reasoning(customer: CustomerProfile) -> dict[str, str | float]`.
- `reason_customer(customer: CustomerProfile, use_openai: bool = False) -> dict[str, str | float]`.
- `evaluate_customer(state: GraphState) -> dict[str, object]` exported from `graph.py` and delegating to the provider.

- [ ] **Step 1: Write failing tests for low/high churn fixtures and API-disabled fallback.**

```python
from models import CustomerProfile
from reasoning import deterministic_reasoning, reason_customer

def test_high_churn_customer_gets_credit_limit_proposal():
    result = deterministic_reasoning(CustomerProfile(toi=80_000_000, churn_probability=0.9))
    assert result["proposed_action"] == "increase_credit_limit"
    assert result["confidence_score"] == 0.96

def test_reason_customer_without_openai_is_local_and_valid():
    result = reason_customer(CustomerProfile(toi=250_000_000, churn_probability=0.2), use_openai=False)
    assert result["proposed_action"] == "send_email"
    assert 0.0 <= result["confidence_score"] <= 1.0
```

- [ ] **Step 2: Run `py -3.13 -m pytest tests/test_reasoning.py -q`; verify failure before implementation.**
- [ ] **Step 3: Implement deterministic thresholds and lazy optional SDK call guarded by `USE_OPENAI`; validate provider JSON and fall back safely.**
- [ ] **Step 4: Run reasoning tests; verify pass and no network call in default mode.**
- [ ] **Step 5: Commit `feat: add deterministic churn reasoning with optional OpenAI adapter`.**

### Task 4: LangGraph routing, interrupt, execution, and resume

**Files:**
- Create: `graph.py`
- Create: `tests/test_graph.py`

**Interfaces:**
- `CONFIDENCE_THRESHOLD: float = 0.85`.
- `route_action(state: GraphState) -> Literal["execute_low_risk_action", "execute_high_risk_action"]`.
- `build_graph(audit_path: str | Path = "audit_log.json", use_openai: bool = False) -> CompiledStateGraph`.
- `new_config(thread_id: str) -> dict`.
- `execute_low_risk_action(state: GraphState) -> dict`.
- `execute_high_risk_action(state: GraphState) -> dict`.

- [ ] **Step 1: Write failing tests for policy precedence and confidence boundary.**

```python
from graph import route_action

def test_credit_limit_is_high_risk_even_at_099():
    assert route_action({"proposed_action": "increase_credit_limit", "confidence_score": 0.99}) == "execute_high_risk_action"

def test_send_email_at_threshold_auto_executes():
    assert route_action({"proposed_action": "send_email", "confidence_score": 0.85}) == "execute_low_risk_action"

def test_send_email_below_threshold_escalates():
    assert route_action({"proposed_action": "send_email", "confidence_score": 0.84}) == "execute_high_risk_action"
```

- [ ] **Step 2: Run `py -3.13 -m pytest tests/test_graph.py -q`; verify expected failure.**
- [ ] **Step 3: Implement graph nodes, `MemorySaver`, conditional edge, interrupt-before compile, safe pending behavior, and audit calls.**
- [ ] **Step 4: Add integration tests that invoke a high-risk customer, assert `get_state(config).next == ("execute_high_risk_action",)`, then update/resume approve, reject, and edit in separate thread IDs; assert execution status and audit entries.**
- [ ] **Step 5: Run `py -3.13 -m pytest tests/test_graph.py -q`; verify all routing and resume tests pass.**
- [ ] **Step 6: Commit `feat: implement interruptible HITL graph`.**

### Task 5: Streamlit app and testable decision helpers

**Files:**
- Create: `app.py`
- Create: `tests/test_app.py`

**Interfaces:**
- `start_customer_workflow(graph, customer: CustomerProfile, config: dict) -> dict`.
- `resume_with_decision(graph, config: dict, decision: str, edited_action: str | None = None, reviewer_id: str = "operator_01") -> dict`.
- `render_app() -> None`.

- [ ] **Step 1: Write failing helper tests for approve/reject/edit payload normalization.**

```python
import pytest
from app import normalize_decision

def test_normalize_decision_requires_edit_value_for_edit():
    with pytest.raises(ValueError, match="edited_action"):
        normalize_decision("Edit", None)

def test_normalize_decision_returns_lowercase_contract():
    assert normalize_decision("Approve", None) == ("approve", None)
```

- [ ] **Step 2: Run `py -3.13 -m pytest tests/test_app.py -q`; verify expected failure.**
- [ ] **Step 3: Implement decision helper, session-scoped graph/thread, action card, buttons, edit input, checkpoint update, resume, and status rendering.**
- [ ] **Step 4: Run app helper tests; verify pass.**
- [ ] **Step 5: Commit `feat: add Streamlit HITL approval interface`.**

### Task 6: CLI demo, README, and full verification

**Files:**
- Create: `run_demo.py`
- Create: `README.md`
- Create: `audit_log.json` containing `[]`
- Modify: `requirements.txt`
- Create: `tests/test_smoke.py`

**Interfaces:**
- `run_demo.py` must run with `py run_demo.py` without an API key and show both an auto-executed and interrupted case.
- README must document exact setup commands for PowerShell, optional OpenAI environment variables, Streamlit launch, threshold 0.85, hard rule, decisions, and audit path.

- [ ] **Step 1: Write failing smoke test that imports the public modules and checks `audit_log.json` is a JSON list.**
- [ ] **Step 2: Run `py -3.13 -m pytest tests/test_smoke.py -q`; verify failure until all modules/files exist.**
- [ ] **Step 3: Implement CLI and README, pin compatible dependency ranges, and initialize empty audit log.**
- [ ] **Step 4: Run the full suite `py -3.13 -m pytest -q`; fix only production defects exposed by tests.**
- [ ] **Step 5: Run `py -3.13 run_demo.py` and `py -3.13 -m compileall -q .`; verify exit code 0 and no secret-like values in tracked files with `rg -n "sk-proj-|OPENAI_API_KEY=" -g '!*.md' .` (the command must return no matches).**
- [ ] **Step 6: Review `git diff --check`, `git status --short`, and commit `docs: add setup and grading runbook`.**

## Completion checklist

- [ ] All required lab symbols exist and are importable.
- [ ] High-risk actions pause before execution and resume only after a human decision.
- [ ] Approve, Reject, and Edit each produce the correct final status and audit entry.
- [ ] Audit history survives multiple appends and malformed files fail safely.
- [ ] Default setup runs without an API key; optional API mode is documented without secrets.
- [ ] Full tests, demo, compile check, and diff check have fresh passing evidence.
