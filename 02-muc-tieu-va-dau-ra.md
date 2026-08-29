# 2. Mục tiêu & đầu ra

Bạn hoàn thành khi xây dựng được một LangGraph workflow đánh giá rủi ro khách hàng rời bỏ (`churn risk`) và xử lý hành động bằng cơ chế Human-in-the-Loop.

## Workflow cần thực hiện

```text
Customer Data
      |
      v
Agent Reasoning
      |
      | proposed_action
      | confidence_score
      | reasoning
      v
Confidence Routing + Hard Rules
      |
      +-----------------------------+
      |                             |
      | Low-risk                    | High-risk / cần review
      v                             v
Auto Execute                  Interrupt Graph
                                    |
                                    v
                             Streamlit Review
                              /      |      \
                         Approve   Reject    Edit
                            |        |        |
                            +--------+--------+
                                     |
                                     v
                                Resume Graph
                                     |
                                     v
                                 Audit Log
```

## Đầu ra cần có

### `GraphState`

Một `GraphState` lưu:

- `customer_id`
- `proposed_action`
- `confidence_score`
- `reasoning`
- `human_decision`

### `AuditEntry`

Một Pydantic `AuditEntry` có:

- `timestamp`
- `agent_id`
- `action`
- `confidence`
- `reviewer_id`
- `decision`

### Node đánh giá khách hàng

```python
evaluate_customer(state)
```

Node này đánh giá khách hàng và trả về:

- `proposed_action`
- `confidence_score`
- `reasoning`

### Conditional routing

```python
route_action(state)
```

Function này thực hiện:

- Policy Override
- Auto-Execute
- Escalate/Suggest

### Compile LangGraph

LangGraph được compile với:

- `MemorySaver()`
- `interrupt_before=["execute_high_risk_action"]`

### Streamlit approval interface

Giao diện cho phép human reviewer:

- Approve
- Reject
- Edit

### Audit trail

Có audit trail ghi lại:

- Quyết định của agent
- Confidence score
- Quyết định của human reviewer
- Reviewer thực hiện quyết định
- Hành động cuối cùng
