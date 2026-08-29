# Churn Risk Human-in-the-Loop Workflow Design

## Goal

Build a runnable LangGraph workflow that evaluates customer churn risk, applies confidence routing with hard policy overrides, pauses high-risk actions for human approval, and records every material decision in an append-only JSON audit trail.

## Scope and success criteria

- A `GraphState` `TypedDict` persists customer inputs, agent proposal, confidence, reasoning, human decision, and execution outcome across graph interrupts.
- A Pydantic `AuditEntry` validates timestamp, agent, action, confidence, reviewer, decision, and optional metadata.
- `evaluate_customer(state)` returns a deterministic proposal from TOI and churn probability. The default path requires no network or credential.
- An optional OpenAI reasoner can be enabled with `USE_OPENAI=true` and a locally configured `OPENAI_API_KEY`; no secret is stored in source, tests, fixtures, or logs.
- `route_action(state)` applies policy precedence: `increase_credit_limit` always routes to high-risk review; low-risk actions at confidence >= 0.85 auto-execute; all other actions escalate.
- The compiled graph uses `MemorySaver()` and `interrupt_before=["execute_high_risk_action"]`.
- Streamlit exposes customer selection/input, proposed action, confidence, reasoning, and Approve/Reject/Edit controls, then resumes the same checkpoint thread.
- Audit writes append entries without overwriting earlier history and use atomic replacement to avoid partial files.
- Unit and integration tests cover schemas, routing boundaries, policy override, deterministic evaluation, pause/resume approve/reject/edit, and audit preservation.
- README explains setup, local run, optional API mode, threshold, policy, UI decisions, and audit location.

## Architecture

### Data and domain models

`models.py` defines `CustomerProfile` (validated TOI and churn probability), `GraphState` (the required lab keys plus optional workflow metadata), and `AuditEntry`. Confidence values are bounded to [0, 1]. Human decisions are normalized to `approve`, `reject`, or `edit`.

### Graph workflow

`graph.py` builds a `StateGraph` with these nodes:

1. `evaluate_customer`: selects the deterministic or optional OpenAI reasoner and records the proposal.
2. `execute_low_risk_action`: performs a simulated side effect and appends an `auto_execute` audit entry.
3. `execute_high_risk_action`: inspects `human_decision`; reject aborts, approve executes the proposed action, and edit executes the reviewer-supplied action. It appends a human audit entry.

The conditional edge after evaluation returns one of the two execute node names. High-risk routing is interrupted before the high-risk node. A stable `thread_id` in the caller's config is required for `get_state`, `update_state`, and resume.

### Reasoning providers

The deterministic provider is the default and is intentionally reproducible for grading. An optional provider in `reasoning.py` lazily imports the official OpenAI Python SDK, reads `OPENAI_API_KEY` from the process environment, requests structured JSON, validates it, and falls back to deterministic reasoning on missing credentials or provider errors. The app never displays or logs the key.

### Audit persistence

`audit.py` exposes `append_audit_entry(entry, path)` and `read_audit_entries(path)`. It reads an existing JSON list (or initializes one), appends the Pydantic-serialized entry, writes a temporary file in the same directory, and replaces the target atomically. Malformed content raises a clear `AuditLogError` rather than silently erasing history.

### Streamlit interface

`app.py` creates one compiled graph and one generated thread ID per Streamlit session. A start action invokes the graph with a selected customer. If the graph is interrupted, the pending state is rendered in an action card. Approve, Reject, and Edit update the checkpoint and resume with `graph.invoke(None, config)`. UI-specific code delegates decisions to testable helpers and displays execution/audit status after resume.

### CLI demonstration

`run_demo.py` runs one low-risk customer and one high-risk customer, showing the pending checkpoint and an optional command-line decision. This gives graders a non-UI smoke-test path.

## Error handling and safety

- Invalid customer values or confidence outside [0, 1] fail validation with actionable messages.
- Unknown actions and human decisions are rejected instead of auto-executed.
- A high-risk action with no human decision remains pending; it cannot execute by accident.
- OpenAI errors never bypass hard policy and fall back to a safe deterministic proposal.
- Audit failures are surfaced to the caller; existing audit history is never replaced with an empty list.
- No API key, access token, password, or real `.env` file is committed.

## Testing strategy

- Schema tests assert validation and required fields.
- Routing tests assert exact boundary behavior at 0.84, 0.85, and policy override at 0.99.
- Evaluation tests use literal customer fixtures and assert proposal/action/confidence/reasoning.
- Graph integration tests use a temporary audit path and stable thread IDs to prove that high-risk execution has not happened at interrupt, state survives, and approve/reject/edit resume correctly.
- Audit tests prove append behavior, malformed-file errors, and preservation of prior entries.
- UI helpers are tested without starting a Streamlit server.

## Setup and configuration

- Supported Python: 3.10+ (development verified with Python 3.13 launcher when available).
- Required packages: `langgraph`, `langchain`, `streamlit`, `pydantic`, `pytest`.
- Optional package: `openai` for API-backed reasoning.
- Default command: `py -m venv .venv`, activate it, `pip install -r requirements.txt`, then `streamlit run app.py`.
- Optional API mode: set `USE_OPENAI=true` and set `OPENAI_API_KEY` in the local shell only. The app remains fully functional without it.

## Out of scope

Real credit-limit changes, email delivery, production database deployment, authentication, and financial decisioning are simulated; the lab demonstrates the HITL control flow and auditability.
