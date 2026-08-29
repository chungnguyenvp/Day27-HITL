"""Local environment loading without overwriting shell-provided values."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_environment(dotenv_path: str | Path = ".env") -> bool:
    """Load optional local configuration and return whether a file was found."""

    return bool(load_dotenv(dotenv_path=Path(dotenv_path), override=False))
