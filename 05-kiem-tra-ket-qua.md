# 5. Kiểm tra kết quả

Nêu cách tự kiểm tra và lỗi thường gặp.

## Kiểm tra State

Đảm bảo `GraphState` có:

```text
customer_id
proposed_action
confidence_score
reasoning
human_decision
```

Kiểm tra:

```text
[ ] State tồn tại xuyên suốt graph
[ ] State không mất khi graph bị interrupt
[ ] human_decision có thể được cập nhật từ Streamlit
```

## Kiểm tra Agent Reasoning

Chạy một customer input.

Đảm bảo agent output:

```text
[ ] proposed_action
[ ] confidence_score
[ ] reasoning
```

và:

```text
0.0 <= confidence_score <= 1.0
```

## Kiểm tra Hard Rule

Test:

```text
proposed_action = increase_credit_limit
confidence_score = 0.99
```

Kết quả bắt buộc:

```text
Human Review
```

Không được:

```text
Auto Execute
```

## Kiểm tra Auto-Execute

Test:

```text
proposed_action = send_email
confidence_score = 0.90
```

Kết quả:

```text
execute_low_risk_action
```

## Kiểm tra Escalation

Test:

```text
proposed_action = send_email
confidence_score = 0.82
```

Kết quả:

```text
Human Review
```

## Kiểm tra Interrupt

Đảm bảo graph compile với:

```python
graph = builder.compile(
    checkpointer=memory,
    interrupt_before=["execute_high_risk_action"]
)
```

Khi route tới high-risk action:

```text
[ ] execute_high_risk_action chưa được chạy
[ ] graph ở pending state
[ ] state vẫn còn dữ liệu customer
```

## Kiểm tra Streamlit

Streamlit UI phải hiển thị:

```text
[ ] proposed_action
[ ] confidence_score
[ ] reasoning
[ ] Approve
[ ] Reject
[ ] Edit
```

### Test Approve

```text
Approve
   |
   v
update_state
   |
   v
resume graph
   |
   v
execute action
```

### Test Reject

```text
Reject
   |
   v
update_state
   |
   v
resume graph
   |
   v
abort action
```

## Kiểm tra Audit Log

Sau mỗi human decision, `audit_log.json` phải có entry mới.

Entry phải chứa:

```text
timestamp
agent_id
action
confidence
reviewer_id
decision
```

Đảm bảo:

```text
[ ] Approve được log
[ ] Reject được log
[ ] Edit được log
[ ] Không overwrite audit history cũ
```

---

# Lỗi thường gặp

## Graph mất state sau khi interrupt

Kiểm tra có dùng:

```python
MemorySaver()
```

và truyền vào:

```python
checkpointer=memory
```

hay chưa.

## High-risk action chạy trước khi human review

Kiểm tra:

```python
interrupt_before=["execute_high_risk_action"]
```

không phải interrupt sau khi action đã được thực hiện.

## Hard rule bị confidence override

Sai:

```text
confidence = 0.99
-> auto execute increase_credit_limit
```

Đúng:

```text
increase_credit_limit
-> luôn human review
```

Hard policy phải được kiểm tra trước confidence threshold.

## Streamlit bấm button nhưng graph không tiếp tục

Kiểm tra:

```python
graph.update_state(config, ...)
```

và sau đó:

```python
graph.invoke(None, config)
```

để resume graph.

## Pending state không lấy được

Kiểm tra:

```python
graph.get_state(config)
```

và `config` phải dùng cùng `thread_id` với lần invoke trước đó.

## Audit log bị ghi đè

Không ghi một object mới đè lên toàn bộ lịch sử.

Cần:

1. Đọc audit entries hiện có.
2. Append `AuditEntry` mới.
3. Ghi lại danh sách.

Trong production nên dùng append-only database.
