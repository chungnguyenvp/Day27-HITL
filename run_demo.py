"""Run the churn HITL workflow from a terminal without Streamlit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from graph import build_graph, new_config
from models import CustomerProfile


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--decision",
        choices=["approve", "reject", "edit"],
        help="Optional decision to resume the high-risk checkpoint.",
    )
    parser.add_argument("--edited-action", default="send_email")
    parser.add_argument("--reviewer-id", default="operator_demo")
    parser.add_argument("--audit-path", default="audit_log.json")
    args = parser.parse_args(argv)

    graph = build_graph(audit_path=Path(args.audit_path))
    low_config = new_config("demo-low")
    low_result = graph.invoke(
        {
            "customer_id": "CUST-LOW",
            "customer": CustomerProfile(
                toi=250_000_000, churn_probability=0.2
            ).model_dump(),
            "human_decision": None,
        },
        low_config,
    )
    print("LOW-RISK AUTO EXECUTION")
    print(json.dumps(low_result, indent=2, ensure_ascii=False, default=str))

    high_config = new_config("demo-high")
    graph.invoke(
        {
            "customer_id": "CUST-HIGH",
            "customer": CustomerProfile(
                toi=80_000_000, churn_probability=0.9
            ).model_dump(),
            "human_decision": None,
        },
        high_config,
    )
    pending = graph.get_state(high_config)
    print("\nHIGH-RISK CHECKPOINT")
    print(json.dumps(pending.values, indent=2, ensure_ascii=False, default=str))
    if args.decision:
        updates = {
            "human_decision": args.decision,
            "reviewer_id": args.reviewer_id,
        }
        if args.decision == "edit":
            updates["edited_action"] = args.edited_action
        result = graph.update_state(high_config, updates)
        resumed = graph.invoke(None, high_config)
        print("\nHUMAN DECISION APPLIED")
        print(json.dumps(resumed, indent=2, ensure_ascii=False, default=str))
    else:
        print(
            "\nPending in this process. Pass --decision approve|reject|edit "
            "to resume during the same invocation."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
