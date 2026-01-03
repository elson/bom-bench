from dataclasses import dataclass
from pathlib import Path


@dataclass
class SandboxConfig:
    """Configuration for a sandbox execution environment."""

    temp_dir: Path | None = None
    keep_on_success: bool = False
    keep_on_failure: bool = True
    timeout: int = 120
    output_dir: Path | None = None


@dataclass
class SandboxResult:
    """Result of a sandbox execution."""

    fixture_name: str
    tool_name: str
    success: bool
    actual_sbom_path: Path | None = None
    duration_seconds: float = 0.0
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    error_message: str | None = None
    sandbox_dir: Path | None = None
