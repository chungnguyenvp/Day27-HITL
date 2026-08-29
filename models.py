"""Validated domain models shared by the graph, UI, and audit repository."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing_extensions import NotRequired


Action = Literal["send_email", "increase_credit_limit"]
Decision = Literal["proposed", "auto_execute", "approve", "reject", "edit"]


class CustomerProfile(BaseModel):
    """Minimal customer signals used by the churn-risk reasoner."""

    model_config = ConfigDict(extra="forbid")

    toi: float = Field(ge=0, description="Total Operating Income in local currency")
    churn_probability: float = Field(ge=0, le=1)
    segment: str = Field(default="standard", min_length=1)


class GraphState(TypedDict):
    """Persistent state passed between LangGraph nodes."""

    customer_id: str
    proposed_action: str
    confidence_score: float
    reasoning: str
    human_decision: str | None
    customer: NotRequired[CustomerProfile | dict[str, Any]]
    reviewer_id: NotRequired[str]
    edited_action: NotRequired[str | None]
    execution_status: NotRequired[str]
    execution_message: NotRequired[str]
    audit_path: NotRequired[str]
    agent_id: NotRequired[str]


class AuditEntry(BaseModel):
    """A single immutable decision record in the local audit trail."""

    model_config = ConfigDict(extra="forbid")

    timestamp: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    action: Action
    confidence: float = Field(ge=0, le=1)
    reviewer_id: str = Field(min_length=1)
    decision: Decision
    customer_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp", "agent_id", "reviewer_id")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized
