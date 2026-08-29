"""Customer reasoning providers with a deterministic, offline default."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from models import Action, CustomerProfile


def deterministic_reasoning(customer: CustomerProfile) -> dict[str, str | float]:
    """Return a reproducible proposal suitable for demos and grading."""

    probability = customer.churn_probability
    toi = customer.toi
    if probability >= 0.75:
        action: Action = "increase_credit_limit"
        confidence = 0.96
        reasoning = (
            f"Customer has high churn probability ({probability:.0%}) and TOI "
            f"of {toi:,.0f}; a credit-limit increase may improve retention."
        )
    elif probability >= 0.5:
        action = "send_email"
        confidence = 0.86
        reasoning = (
            f"Customer has moderate churn probability ({probability:.0%}) and TOI "
            f"of {toi:,.0f}; send a targeted retention email."
        )
    else:
        action = "send_email"
        confidence = 0.92
        reasoning = (
            f"Customer has low churn probability ({probability:.0%}) and TOI "
            f"of {toi:,.0f}; a low-risk check-in email is appropriate."
        )
    return {
        "proposed_action": action,
        "confidence_score": confidence,
        "reasoning": reasoning,
    }


def _validated_result(payload: Any) -> dict[str, str | float]:
    if not isinstance(payload, dict):
        raise ValueError("reasoner response must be a JSON object")
    action = payload.get("proposed_action")
    confidence = payload.get("confidence_score")
    reasoning = payload.get("reasoning")
    if action not in {"send_email", "increase_credit_limit"}:
        raise ValueError("reasoner returned an unsupported action")
    try:
        confidence = float(confidence)
    except (TypeError, ValueError) as exc:
        raise ValueError("reasoner confidence must be numeric") from exc
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("reasoner confidence must be between 0 and 1")
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise ValueError("reasoner reasoning must be non-empty text")
    return {
        "proposed_action": action,
        "confidence_score": confidence,
        "reasoning": reasoning.strip(),
    }


def _openai_reasoning(customer: CustomerProfile) -> dict[str, str | float]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("optional package 'openai' is not installed") from exc

    prompt = (
        "Evaluate this customer for churn risk. Return JSON only with keys "
        "proposed_action (send_email or increase_credit_limit), "
        "confidence_score (0 to 1), and reasoning. "
        f"TOI={customer.toi}; churn_probability={customer.churn_probability}."
    )
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        input=prompt,
    )
    output_text = getattr(response, "output_text", "")
    match = re.search(r"\{.*\}", output_text, flags=re.DOTALL)
    if not match:
        raise ValueError("OpenAI response did not contain a JSON object")
    return _validated_result(json.loads(match.group(0)))


def reason_customer(
    customer: CustomerProfile, use_openai: bool = False
) -> dict[str, str | float]:
    """Use OpenAI only when explicitly requested; otherwise stay offline."""

    if not use_openai:
        return deterministic_reasoning(customer)
    try:
        return _openai_reasoning(customer)
    except Exception:
        # Provider/network/validation failures must not block a safe demo or
        # change the policy route. The deterministic result remains auditable.
        return deterministic_reasoning(customer)
