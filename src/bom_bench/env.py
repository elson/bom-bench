"""Environment variable handling and interpolation."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


def load_dotenv(path: Path) -> dict[str, str]:
    """Load environment variables from a .env file. Returns empty dict if file doesn't exist."""
    if not path.exists():
        return {}

    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()

        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]

        env[key] = value

    return env


VAR_PATTERN = re.compile(r"\$\{([^}:]+)(?::-([^}]*))?\}")


def interpolate_value(value: str, env: dict[str, str] | None = None) -> str:
    """Interpolate ${VAR} and ${VAR:-default} syntax. Raises ValueError if var missing."""
    combined_env = {**os.environ, **(env or {})}

    def replacer(match: re.Match[str]) -> str:
        var_name, default = match.group(1), match.group(2)
        if var_name in combined_env:
            return combined_env[var_name]
        if default is not None:
            return default
        raise ValueError(f"Environment variable '{var_name}' is not set")

    return VAR_PATTERN.sub(replacer, value)


def interpolate_dict(data: dict[str, Any], env: dict[str, str] | None = None) -> dict[str, Any]:
    """Recursively interpolate all string values in a dictionary."""

    def interpolate_item(item: Any) -> Any:
        if isinstance(item, str):
            return interpolate_value(item, env)
        if isinstance(item, dict):
            return interpolate_dict(item, env)
        if isinstance(item, list):
            return [interpolate_item(i) for i in item]
        return item

    return {key: interpolate_item(value) for key, value in data.items()}


def get_project_env(project_root: Path) -> dict[str, str]:
    """Get combined environment from .env file and OS (dotenv takes precedence)."""
    return {**os.environ, **load_dotenv(project_root / ".env")}
