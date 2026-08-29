# Day 27 · Churn Risk Human-in-the-Loop

LangGraph workflow đánh giá rủi ro khách hàng rời bỏ (churn), định tuyến theo confidence + hard policy, dừng trước hành động rủi ro cao để người vận hành Approve/Reject/Edit, và ghi audit trail append-only.

## Tính năng

- `GraphState` dạng `TypedDict` giữ customer data, proposed action, confidence, reasoning và human decision xuyên suốt checkpoint.
- `AuditEntry` Pydantic validation với timestamp, agent, action, confidence, reviewer và decision.
- Reasoning deterministic mặc định, chạy offline và không cần API key.
- Optional OpenAI reasoner (lazy import, fallback an toàn về deterministic nếu thiếu key/lỗi mạng).
- Hard rule: `increase_credit_limit` luôn phải human review, kể cả confidence 0.99.
- Auto-execute: chỉ `send_email` với confidence >= **0.85**.
- Confidence thấp hơn 0.85 được escalate tới human review.
- `MemorySaver()` + `interrupt_before=["execute_high_risk_action"]` bảo đảm hành động high-risk chưa chạy trước khi duyệt.
- Streamlit dashboard và CLI demo.
- Audit JSON append-only với ghi file atomic; lịch sử cũ không bị overwrite.

## Setup (Windows PowerShell)

Yêu cầu Python 3.10+. Nếu `python` không có trong PATH, dùng Python Launcher:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Nếu PowerShell chặn activation, chạy trực tiếp `\.venv\Scripts\python.exe -m pip install -r requirements.txt`.

## Chạy Streamlit

```powershell
streamlit run app.py
```

Chọn customer preset, bấm **Evaluate customer**. Với high-risk/policy override, action card sẽ pause và hiện **Approve**, **Reject**, **Edit & apply**. Edit chỉ nhận action hợp lệ (`send_email` hoặc `increase_credit_limit`). Reviewer ID được lưu trong audit.

## Chạy CLI demo

Không cần API key:

```powershell
py run_demo.py
py run_demo.py --decision approve --reviewer-id operator_01
py run_demo.py --decision edit --edited-action send_email
py run_demo.py --decision reject
```

Demo luôn hiển thị một low-risk auto execution và một high-risk pending checkpoint trước khi (tuỳ chọn) resume.

## OpenAI mode (tuỳ chọn)

Không gửi key vào chat, source code hoặc Git. Hãy revoke key đã từng dán trong hội thoại và tự tạo key mới nếu cần. API mode chỉ bật khi bạn tự đặt biến môi trường trên máy:

```powershell
Copy-Item .env.example .env
notepad .env
```

Trong `.env`, điền `OPENAI_API_KEY` mới, đặt `USE_OPENAI=true` nếu muốn bật mặc định (và có thể đổi `OPENAI_MODEL`). File `.env` đã được ignore bởi Git. Nếu không muốn dùng file, có thể set `$env:OPENAI_API_KEY` trong PowerShell thay thế. Cài SDK tùy chọn bằng `python -m pip install "openai>=1.0,<2.0"`.

Trong app, bật **Use OpenAI reasoner (optional)**. Key chỉ được SDK đọc từ environment phía server; app không hiển thị hoặc ghi key vào log. Thiếu key/lỗi provider sẽ tự fallback deterministic, và hard policy vẫn được áp dụng.

## Audit log

Mặc định lưu tại `audit_log.json` ở project root. Có thể đổi bằng:

```powershell
$env:AUDIT_LOG_PATH = "data/audit.json"
```

Mỗi entry có `timestamp`, `agent_id`, `action`, `confidence`, `reviewer_id`, `decision`, `customer_id` và metadata. Các decision gồm `auto_execute`, `approve`, `reject`, `edit`.

## Kiểm thử

```powershell
py -3.13 -m pytest -q
py -3.13 -m compileall -q .
```

Test bao phủ schema validation, routing boundary 0.84/0.85, hard-rule override, MemorySaver interrupt/resume, cả ba human decisions, audit append/preserve/malformed safety và UI decision helpers.

## Nộp bài

Không commit API key, access token, password hoặc `.env` thật. Repository cần có tối thiểu `graph.py`, `models.py`, `app.py`, `audit_log.json`, `requirements.txt`, test và README này.
