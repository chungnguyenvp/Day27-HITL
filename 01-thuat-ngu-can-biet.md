# 1. Thuật ngữ cần biết

## Bản đồ Lab

### Đọc trước khi bắt đầu

**120 phút · Trung cấp**

Xây dựng một LangGraph workflow cho bài toán đánh giá churn risk của khách hàng, kết hợp agent reasoning, confidence routing, hard policy rules, human approval bằng Streamlit và audit logging.

## Bài này đang nói về điều gì?

- Thiết kế persistent state cho LangGraph bằng `TypedDict`
- Thiết kế audit schema bằng Pydantic
- Xây dựng agent reasoning node với action, confidence score và reasoning
- Kết hợp confidence routing với hard policy rules
- Dùng `interrupt_before` và `MemorySaver` để triển khai Human-in-the-Loop
- Xây dựng giao diện Approve, Reject và Edit bằng Streamlit
- Ghi lại quyết định của agent và con người vào audit trail

### Luồng tổng quát

1. **Customer data -> Agent reasoning -> Proposed action + confidence score**
2. **Hard rules và confidence routing -> Auto-execute hoặc chuyển sang human review**
3. **LangGraph interrupt -> Streamlit approval interface -> Approve, Reject hoặc Edit**
4. **Resume graph -> Execute/abort action -> Audit log**

## Buổi Lab diễn ra như thế nào?

### 1. State và Audit Schema — 20 phút · Cá nhân

Định nghĩa `GraphState` và `AuditEntry` để lưu trạng thái workflow và dữ liệu audit.

### 2. Agent Reasoning và Routing — 25 phút · Cá nhân

Xây dựng node đánh giá khách hàng, confidence score và conditional routing kết hợp hard rules.

### 3. Compile Graph với Interrupts — 25 phút · Cá nhân

Sử dụng `MemorySaver` và `interrupt_before` để dừng workflow trước hành động high-risk.

### 4. Streamlit Human Approval — 30 phút · Cá nhân

Xây dựng giao diện cho human operator xem, Approve, Reject hoặc Edit pending action.

### 5. Audit Log và kiểm tra — 20 phút · Cá nhân

Ghi lại quyết định vào audit trail và kiểm tra toàn bộ luồng Human-in-the-Loop.

## Kết thúc bài, bạn có gì?

- Xây dựng được LangGraph workflow có persistent state
- Agent đưa ra proposed action, reasoning và confidence score
- Workflow áp dụng hard policy rules và confidence routing
- High-risk action bị dừng để chờ human approval
- Human operator có thể Approve, Reject hoặc Edit action qua Streamlit
- Mọi quyết định được lưu vào audit trail

## Chưa cần lo

Không cần xây một hệ thống ngân hàng hoàn chỉnh. Trọng tâm của Lab là hiểu đúng luồng Human-in-the-Loop: agent đề xuất, policy quyết định route, graph tạm dừng khi cần và con người đưa ra quyết định cuối cùng trước hành động rủi ro cao.

## Bảng thuật ngữ

| Thuật ngữ gốc | Bản chất khái niệm | Minh hoạ trực quan |
|---|---|---|
| **`Human-in-the-Loop (HITL)`** | Kiến trúc trong đó AI không được tự thực hiện mọi hành động mà phải chuyển một số quyết định cho con người kiểm tra trước khi tiếp tục. | Agent đề xuất tăng hạn mức tín dụng nhưng workflow dừng lại để nhân viên ngân hàng Approve hoặc Reject. |
| **`LangGraph`** | Framework xây workflow dạng graph cho agent, cho phép quản lý state, routing, checkpoint và tạm dừng/resume execution. | Customer data đi qua các node đánh giá -> routing -> human review -> execution. |
| **`GraphState`** | Trạng thái dùng chung được truyền qua các node trong graph và lưu thông tin cần thiết của workflow. | Lưu `customer_id`, `proposed_action`, `confidence_score`, `reasoning`, `human_decision`. |
| **`TypedDict`** | Cách khai báo cấu trúc dictionary có kiểu dữ liệu rõ ràng trong Python. | Dùng để mô tả chính xác các field tồn tại trong `GraphState`. |
| **`AuditEntry`** | Schema đại diện cho một bản ghi audit để biết agent đã đề xuất gì, confidence bao nhiêu và con người quyết định thế nào. | Một record có `timestamp`, `agent_id`, `action`, `confidence`, `reviewer_id`, `decision`. |
| **`Confidence Score`** | Điểm thể hiện mức độ tự tin của agent đối với quyết định của mình, thường nằm từ 0.0 đến 1.0. | `0.92` có thể auto-execute low-risk action, còn `0.72` phải human review. |
| **`Confidence Routing`** | Cơ chế dùng confidence score để quyết định workflow đi sang nhánh nào. | Confidence >= 0.85 và action low-risk -> auto execute. |
| **`Hard Rule`** | Quy tắc cứng có độ ưu tiên cao hơn confidence của agent. | `increase_credit_limit` luôn phải human review dù confidence là 0.99. |
| **`Policy Override`** | Trường hợp policy cưỡng chế route, không cho confidence của agent quyết định. | Action tăng hạn mức luôn đi tới high-risk path. |
| **`MemorySaver`** | Checkpointer của LangGraph dùng để lưu state để workflow có thể tạm dừng và tiếp tục sau đó. | Graph dừng trước high-risk action nhưng customer data không bị mất khi chờ người review. |
| **`interrupt_before`** | Cấu hình yêu cầu LangGraph dừng trước khi chạy một node cụ thể. | `interrupt_before=["execute_high_risk_action"]` dừng graph trước khi hành động nguy hiểm được thực thi. |
| **`Pending State`** | Trạng thái workflow đang tạm dừng để chờ quyết định từ bên ngoài. | Streamlit lấy pending state và hiển thị proposed action cho reviewer. |
| **`Audit Trail`** | Nhật ký bất biến hoặc có thể kiểm toán về các quyết định và hành động đã diễn ra trong workflow. | Ghi agent đề xuất gì, confidence bao nhiêu, ai review và quyết định cuối cùng là gì. |
| **`Approve`** | Human reviewer đồng ý với proposed action và cho workflow tiếp tục. | Cho phép thực hiện `increase_credit_limit`. |
| **`Reject`** | Human reviewer từ chối proposed action và yêu cầu workflow hủy hành động. | Không thực hiện thay đổi hạn mức tín dụng. |
| **`Edit`** | Human reviewer sửa proposed action trước khi workflow tiếp tục. | Agent đề xuất tăng 50 triệu, reviewer sửa thành tăng 20 triệu rồi approve. |
