"""Safe local persistence for the append-only audit trail."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from pydantic import ValidationError

from models import AuditEntry


class AuditLogError(RuntimeError):
    """Raised when an audit log cannot be read or validated safely."""


def _path(path: str | Path) -> Path:
    return Path(path).expanduser()


def read_audit_entries(path: str | Path = "audit_log.json") -> list[AuditEntry]:
    target = _path(path)
    if not target.exists():
        return []
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuditLogError(f"Unable to read audit log {target}: {exc}") from exc
    if not isinstance(raw, list):
        raise AuditLogError(f"Audit log {target} must contain a JSON list")
    try:
        return [AuditEntry.model_validate(item) for item in raw]
    except (TypeError, ValidationError) as exc:
        raise AuditLogError(f"Audit log {target} contains an invalid entry: {exc}") from exc


def append_audit_entry(
    entry: AuditEntry, path: str | Path = "audit_log.json"
) -> AuditEntry:
    target = _path(path)
    entries = read_audit_entries(target)
    entries.append(entry)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_name = temporary.name
            json.dump(
                [item.model_dump(mode="json") for item in entries],
                temporary,
                ensure_ascii=False,
                indent=2,
            )
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, target)
    except (OSError, TypeError, ValueError) as exc:
        if temporary_name:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
        raise AuditLogError(f"Unable to append audit log {target}: {exc}") from exc
    return entry
