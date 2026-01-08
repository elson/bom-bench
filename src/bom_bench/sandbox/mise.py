import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import tomlkit


@dataclass
class ToolSpec:
    """Specification for a mise-managed tool."""

    name: str
    version: str


@dataclass
class MiseRunResult:
    """Result of running a mise task."""

    success: bool
    exit_code: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    error_message: str | None = None


def generate_mise_toml(
    tools: list[ToolSpec],
    env: dict[str, str] | None = None,
    task_name: str | None = None,
    task_command: str | None = None,
) -> str:
    """Generate mise.toml content from configuration.

    Args:
        tools: List of tool specifications (name, version)
        env: Environment variables to set
        task_name: Optional task name to create
        task_command: Command string for the task (required if task_name is set)

    Returns:
        TOML string content for mise.toml
    """
    if not tools and not env and not task_name:
        return ""

    doc = tomlkit.document()

    if tools:
        tools_table = tomlkit.table()
        for tool in tools:
            tools_table[tool.name] = tool.version
        doc["tools"] = tools_table

    if env:
        env_table = tomlkit.table()
        for name, value in env.items():
            env_table[name] = value
        doc["env"] = env_table

    if task_name and task_command:
        tasks_table = tomlkit.table()
        task_config = tomlkit.table()
        task_config["run"] = task_command
        tasks_table[task_name] = task_config
        doc["tasks"] = tasks_table

    return tomlkit.dumps(doc)


class MiseRunner:
    """Wrapper for running mise commands in a directory."""

    def __init__(self, cwd: Path):
        self.cwd = cwd

    def _get_sandboxed_env(self) -> dict[str, str]:
        """Get environment variables with MISE_CEILING_PATHS set for isolation.

        Sets MISE_CEILING_PATHS to the sandbox directory to prevent mise from
        loading configuration files from parent directories.
        """
        env = os.environ.copy()
        env["MISE_CEILING_PATHS"] = str(self.cwd)
        return env

    def run_task(self, task_name: str, timeout: int = 120) -> MiseRunResult:
        """Run a mise task.

        Args:
            task_name: Name of the task to run (e.g., "sca")
            timeout: Maximum execution time in seconds

        Returns:
            MiseRunResult with execution details
        """
        if not shutil.which("mise"):
            return MiseRunResult(
                success=False,
                exit_code=None,
                stdout="",
                stderr="",
                duration_seconds=0.0,
                error_message="mise not found in PATH",
            )

        start_time = time.time()

        try:
            result = subprocess.run(
                ["mise", "run", task_name],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._get_sandboxed_env(),
            )

            duration = time.time() - start_time

            return MiseRunResult(
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return MiseRunResult(
                success=False,
                exit_code=None,
                stdout="",
                stderr="",
                duration_seconds=duration,
                error_message=f"Timeout after {timeout} seconds",
            )

        except Exception as e:
            duration = time.time() - start_time
            return MiseRunResult(
                success=False,
                exit_code=None,
                stdout="",
                stderr="",
                duration_seconds=duration,
                error_message=str(e),
            )

    def trust(self) -> bool:
        """Trust the mise.toml in the current directory.

        Required before mise will execute tasks with untrusted configs.

        Returns:
            True if trust succeeded, False otherwise
        """
        if not shutil.which("mise"):
            return False

        try:
            result = subprocess.run(
                ["mise", "trust"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=10,
                env=self._get_sandboxed_env(),
            )
            return result.returncode == 0
        except Exception:
            return False

    def write_mise_toml(
        self,
        tools: list[ToolSpec],
        env: dict[str, str] | None = None,
        task_name: str | None = None,
        task_command: str | None = None,
    ) -> Path:
        """Generate and write mise.toml to the working directory.

        Args:
            tools: List of tool specifications
            env: Environment variables to set
            task_name: Optional task name
            task_command: Command for the task

        Returns:
            Path to the written mise.toml file
        """
        content = generate_mise_toml(
            tools=tools,
            env=env,
            task_name=task_name,
            task_command=task_command,
        )

        mise_toml_path = self.cwd / "mise.toml"
        mise_toml_path.write_text(content)

        return mise_toml_path
