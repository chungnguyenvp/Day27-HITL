# 3. Chuẩn bị

Liệt kê công cụ, dữ liệu và điều kiện tối thiểu.

## Python

Yêu cầu:

```text
Python 3.10+
```

## Thư viện

Cài các thư viện:

```bash
pip install langgraph langchain streamlit pydantic
```

Các thư viện chính:

```text
langgraph
langchain
streamlit
pydantic
```

## Cấu trúc project gợi ý

```text
day27-hitl/
├── app.py
├── graph.py
├── models.py
├── audit_log.json
└── requirements.txt
```

## Vai trò từng file

### `graph.py`

Chứa:

- `GraphState`
- Agent nodes
- Routing
- Graph compilation

### `models.py`

Chứa:

- `AuditEntry`

### `app.py`

Chứa:

- Streamlit UI
- Human approval logic
- Resume graph logic

### `audit_log.json`

Chứa:

- Audit trail
