# 4. Thực hành

## Bước 1 - Định nghĩa State và Audit Schema

Graph cần một persistent state để giữ proposed action của agent trong khi chờ human approval.

Tạo một `GraphState` sử dụng `TypedDict`.

State bao gồm các key:

```text
customer_id
proposed_action
confidence_score
reasoning
human_decision
```

Ví dụ:

```python
from typing import TypedDict

class GraphState(TypedDict):
    customer_id: str
    proposed_action: str
    confidence_score: float
    reasoning: str
    human_decision: str | None
```

`GraphState` cần tồn tại xuyên suốt workflow.

Ví dụ:

```text
Agent đề xuất action
        |
        v
GraphState
        |
        | graph tạm dừng
        v
Human Review
        |
        | cập nhật decision
        v
GraphState
```

Tiếp theo, định nghĩa một Pydantic `BaseModel` có tên:

```text
AuditEntry
```

bao gồm:

```text
timestamp
agent_id
action
confidence
reviewer_id
decision
```

Ví dụ:

```python
from pydantic import BaseModel

class AuditEntry(BaseModel):
    timestamp: str
    agent_id: str
    action: str
    confidence: float
    reviewer_id: str
    decision: str
```

Mục tiêu của audit schema là lưu lại đầy đủ:

```text
Agent nào đưa ra quyết định?
Hành động được đề xuất là gì?
Confidence bao nhiêu?
Ai review?
Human quyết định gì?
Thời điểm nào?
```

---

## Bước 2 - Implement Agent Reasoning Node

Giả lập một agent đánh giá:

```text
Total Operating Income (TOI)
```

và:

```text
churn probability
```

của khách hàng.

Tạo một node function:

```python
evaluate_customer(state)
```

Ví dụ:

```python
def evaluate_customer(state: GraphState):
    ...
```

Có thể:

- Hardcode một mock LLM output.
- Hoặc sử dụng một prompt cơ bản để generate mock output.

Agent cần đề xuất một action.

Action có thể là:

```text
send_email
```

cho trường hợp:

```text
low-risk
```

hoặc:

```text
increase_credit_limit
```

cho trường hợp:

```text
high-risk
```

Node phải output một:

```text
confidence_score
```

trong khoảng:

```text
0.0 -> 1.0
```

Ví dụ output:

```python
{
    "proposed_action": "send_email",
    "confidence_score": 0.92,
    "reasoning": "Customer has moderate churn probability and no high-risk financial action is required."
}
```

Hoặc:

```python
{
    "proposed_action": "increase_credit_limit",
    "confidence_score": 0.96,
    "reasoning": "Customer has high churn probability and increasing the credit limit may improve retention."
}
```

Lưu ý:

```text
confidence_score cao KHÔNG có nghĩa là agent được phép bypass policy.
```

Hard policy rule ở bước tiếp theo có quyền override confidence.

---

## Bước 3 - Implement Confidence Routing và Hard Rules

Tạo một conditional edge function:

```python
route_action(state)
```

để xác định bước tiếp theo dựa trên output của agent.

Ví dụ:

```python
def route_action(state: GraphState):
    ...
```

Routing phải thực hiện ba rule.

### Rule 1 - Policy Override

Nếu action là:

```text
increase_credit_limit
```

thì route thẳng đến:

```text
execute_high_risk_action
```

bất kể:

```text
confidence_score
```

là bao nhiêu.

Ví dụ:

```text
action = increase_credit_limit
confidence = 0.99
```

vẫn phải:

```text
Human Review
```

Không được auto-execute.

Luồng:

```text
increase_credit_limit
        |
        | hard policy rule
        v
execute_high_risk_action
        |
        | interrupt_before
        v
Human Review
```

### Rule 2 - Auto-Execute

Nếu:

```text
confidence_score >= 0.85
```

và action là:

```text
low-risk
```

thì route đến:

```text
execute_low_risk_action
```

Ví dụ:

```text
action = send_email
confidence_score = 0.91
```

thì:

```text
Auto Execute
```

### Rule 3 - Escalate/Suggest

Nếu:

```text
confidence_score < 0.85
```

thì route đến:

```text
execute_high_risk_action
```

để ép buộc human review.

Ví dụ:

```text
action = send_email
confidence_score = 0.82
```

mặc dù action là low-risk nhưng confidence thấp hơn threshold nên:

```text
Human Review
```

### Tóm tắt routing

```text
                     proposed_action
                            |
                            v
                +-------------------------+
                | increase_credit_limit ? |
                +-------------------------+
                     | YES          | NO
                     v              v
                 High Risk     confidence >= 0.85 ?
                                      |
                               +------+------+
                               |             |
                              YES            NO
                               |             |
                               v             v
                          Low Risk       High Risk
```

---

## Bước 4 - Compile Graph với Interrupts

Đây là phần lõi của HITL architecture.

Bạn phải pause graph trước khi bất kỳ destructive action hoặc high-risk action nào diễn ra.

Khởi tạo:

```python
MemorySaver()
```

checkpointer.

Import:

```python
from langgraph.checkpoint.memory import MemorySaver
```

Khởi tạo:

```python
memory = MemorySaver()
```

Điều này là bắt buộc.

Nếu không có persistent checkpoint, graph có thể mất customer data trong khi chờ con người review.

Build state graph và kết nối các node.

Các node có thể gồm:

```text
evaluate_customer
execute_low_risk_action
execute_high_risk_action
```

Sau đó compile graph:

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()

graph = builder.compile(
    checkpointer=memory,
    interrupt_before=["execute_high_risk_action"]
)
```

Điểm quan trọng:

```python
interrupt_before=["execute_high_risk_action"]
```

có nghĩa là:

- Graph **KHÔNG** chạy `execute_high_risk_action` ngay.
- Graph dừng **TRƯỚC** node đó.

Luồng:

```text
evaluate_customer
       |
       v
route_action
       |
       v
execute_high_risk_action
       X
       |
       | INTERRUPT BEFORE
       v
Human Review
```

State phải vẫn tồn tại trong lúc graph đang tạm dừng.

---

## Bước 5 - Xây dựng Streamlit Approval Interface

Tạo một front-end dashboard nơi human operator review các pending actions.

Tạo:

```text
app.py
```

Setup một Streamlit app.

Ví dụ chạy:

```bash
streamlit run app.py
```

Khởi tạo compiled graph trong:

```python
session_state
```

để graph không bị tạo lại không cần thiết mỗi lần Streamlit rerun.

Sử dụng:

```python
graph.get_state(config)
```

để lấy pending state hiện tại.

Trích xuất:

```text
proposed_action
confidence_score
reasoning
```

Render một Action Card trong Streamlit.

Ví dụ thông tin:

```text
Customer ID: CUST001

Proposed Action:
increase_credit_limit

Confidence:
0.91

Reasoning:
Customer has high churn probability...
```

Thêm ba button:

```text
Approve
Reject
Edit
```

### Approve

Human operator đồng ý với action.

Ví dụ:

```python
human_decision = "approve"
```

### Reject

Human operator từ chối action.

Ví dụ:

```python
human_decision = "reject"
```

### Edit

Human operator chỉnh sửa proposed action trước khi tiếp tục.

Ví dụ:

```text
Agent:
increase_credit_limit = 50,000,000

Human Edit:
increase_credit_limit = 20,000,000
```

Khi một button được click, trigger:

```python
graph.update_state(
    config,
    {"human_decision": decision}
)
```

Sau đó invoke graph lại:

```python
graph.invoke(None, config)
```

để resume execution.

Luồng:

```text
Graph interrupted
       |
       v
Streamlit UI
       |
       +-------- Approve
       |
       +-------- Reject
       |
       +-------- Edit
       |
       v
graph.update_state(...)
       |
       v
graph.invoke(None, config)
       |
       v
Resume Graph
```

---

## Bước 6 - Ghi Audit Log

Chỉnh sửa node:

```text
execute_high_risk_action
```

để kiểm tra:

```python
state["human_decision"]
```

Nếu decision là:

```text
Approve
```

thì:

```text
execute action
```

Ví dụ:

```text
increase_credit_limit
```

được phép thực hiện.

Nếu decision là:

```text
Reject
```

thì:

```text
abort action
```

Không thực hiện proposed action.

Nếu decision là:

```text
Edit
```

thì thực hiện action sau khi đã được human operator chỉnh sửa.

Trong tất cả các trường hợp, khởi tạo một:

```text
AuditEntry
```

và append vào một file JSON cục bộ.

Ví dụ:

```json
{
  "timestamp": "2026-08-29T09:00:00",
  "agent_id": "churn-risk-agent",
  "action": "increase_credit_limit",
  "confidence": 0.94,
  "reviewer_id": "operator_01",
  "decision": "approve"
}
```

File:

```text
audit_log.json
```

có thể có dạng:

```json
[
  {
    "timestamp": "2026-08-29T09:00:00",
    "agent_id": "churn-risk-agent",
    "action": "increase_credit_limit",
    "confidence": 0.94,
    "reviewer_id": "operator_01",
    "decision": "approve"
  }
]
```

Mục tiêu:

```text
Mọi quyết định quan trọng phải truy vết được.
```

Trong production, có thể ghi log vào:

```text
PostgreSQL append-only database
```

để tăng độ tin cậy và khả năng kiểm toán.

---

# Reflection Questions

## Câu 1

Ở Bước 4, chúng ta đã dùng:

```python
interrupt_before=["execute_high_risk_action"]
```

Nếu mục tiêu của bạn là để con người rewrite một customer retention email vừa được generate trước khi nó di chuyển đến một routing node, bạn sẽ dùng:

```text
interrupt_before
```

hay:

```text
interrupt_after
```

Tại sao?

## Câu 2

Giả sử Streamlit UI của bạn hiện đang ép human phải review:

```text
500 actions send_email mỗi ngày
```

vì confidence của agent bị kẹt ở:

```text
0.82
```

ngay dưới threshold:

```text
0.85
```

Hãy thay đổi cụ thể về UI/UX hoặc architecture nào bạn có thể thực hiện để ngăn chặn:

```text
Alert Fatigue
```

(Hội chứng mệt mỏi vì cảnh báo)?

## Câu 3

Bạn nhận thấy agent thường xuyên tự báo confidence là:

```text
0.95
```

khi đề xuất:

```text
increase_credit_limit
```

nhưng nó lại thường xuyên sai về thu nhập thực tế của khách hàng.

Tại sao việc chỉ phụ thuộc vào sự tự đánh giá confidence của LLM lại nguy hiểm?

Và làm thế nào bạn có thể calibrate điểm số này trước bước routing?
