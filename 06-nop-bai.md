# 6. Nộp bài

Hình thức: cá nhân.

## Artefact cần nộp

- Link repository GitHub cá nhân chứa bài làm Lab 27.

Repository cần có tối thiểu:

```text
GraphState
AuditEntry
evaluate_customer
route_action
execute_low_risk_action
execute_high_risk_action
MemorySaver
interrupt_before
Streamlit approval interface
audit log
```

## README cần mô tả

- Cách cài dependency.
- Cách chạy LangGraph workflow.
- Cách chạy Streamlit UI.
- Confidence threshold đang sử dụng.
- Hard policy rule.
- Cách Approve, Reject và Edit.
- Audit log được lưu ở đâu.

Ví dụ chạy:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Repository không nên chứa

```text
API key
Access token
Password
Private key
.env chứa credential thật
```

## Ví dụ link nộp

```text
https://github.com/<YOUR_USERNAME>/Day27-HITL
```
