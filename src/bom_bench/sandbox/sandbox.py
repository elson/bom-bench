import shutil
import tempfile
from pathlib import Path

from bom_bench.models.fixture import Fixture, FixtureSetEnvironment
from bom_bench.models.sandbox import SandboxConfig, SandboxResult
from bom_bench.models.sca_tool import SCAToolConfig
from bom_bench.sandbox.mise import MiseRunner, generate_mise_toml


class Sandbox:
    """Isolated execution environment for benchmarking.

    Creates a temporary directory, generates mise.toml with combined
    fixture + SCA tool environments, copies fixture files, executes
    the SCA tool via mise run, and cleans up.

    Usage:
        with Sandbox(fixture, fixture_env, sca_tool, config) as sandbox:
            result = sandbox.run()
    """

    def __init__(
        self,
        fixture: Fixture,
        fixture_env: FixtureSetEnvironment,
        sca_tool: SCAToolConfig,
        config: SandboxConfig | None = None,
    ):
        self.fixture = fixture
        self.fixture_env = fixture_env
        self.sca_tool = sca_tool
        self.config = config or SandboxConfig()

        self._sandbox_dir: Path | None = None
        self._should_cleanup: bool = True

    @property
    def sandbox_dir(self) -> Path | None:
        """The sandbox directory (available after entering context)."""
        return self._sandbox_dir

    @property
    def project_dir(self) -> Path:
        """Directory containing the copied project files."""
        if self._sandbox_dir is None:
            raise RuntimeError("Sandbox not initialized. Use as context manager.")
        return self._sandbox_dir / "project"

    @property
    def output_path(self) -> Path:
        """Path where the SCA tool should write its output."""
        if self._sandbox_dir is None:
            raise RuntimeError("Sandbox not initialized. Use as context manager.")
        return self._sandbox_dir / "actual.cdx.json"

    def __enter__(self) -> "Sandbox":
        """Set up the sandbox environment."""
        if self.config.temp_dir:
            self._sandbox_dir = self.config.temp_dir
            self._sandbox_dir.mkdir(parents=True, exist_ok=True)
        else:
            self._sandbox_dir = Path(tempfile.mkdtemp(prefix="bom-bench-"))

        self._generate_mise_toml()
        self._copy_fixture_files()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ARG002
        """Clean up the sandbox environment."""
        if self._sandbox_dir is None:
            return

        success = exc_type is None
        should_keep = (success and self.config.keep_on_success) or (
            not success and self.config.keep_on_failure
        )

        if should_keep:
            self._should_cleanup = False
        else:
            shutil.rmtree(self._sandbox_dir, ignore_errors=True)

    def run(self) -> SandboxResult:
        """Execute the SCA tool in the sandbox environment.

        Returns:
            SandboxResult with execution details
        """
        return self._execute_sca_tool()

    def _execute_sca_tool(self) -> SandboxResult:
        """Run the SCA tool via mise."""
        if self._sandbox_dir is None:
            raise RuntimeError("Sandbox not initialized. Use as context manager.")

        runner = MiseRunner(cwd=self._sandbox_dir)
        runner.trust()

        result = runner.run_task("sca", timeout=self.config.timeout)

        # Copy SBOM to output directory if successful and output_dir is configured
        final_sbom_path: Path | None = None
        if result.success and self.output_path.exists():
            if self.config.output_dir:
                # Copy to persistent output directory before cleanup
                final_sbom_path = self.config.output_dir / "actual.cdx.json"
                final_sbom_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.output_path, final_sbom_path)
            else:
                # No output_dir configured, use sandbox path (may be deleted)
                final_sbom_path = self.output_path

        return SandboxResult(
            fixture_name=self.fixture.name,
            tool_name=self.sca_tool.name,
            success=result.success and self.output_path.exists(),
            actual_sbom_path=final_sbom_path,
            duration_seconds=result.duration_seconds,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            error_message=result.error_message,
            sandbox_dir=self._sandbox_dir if not self._should_cleanup else None,
        )

    def _generate_mise_toml(self) -> None:
        """Generate mise.toml with combined environment."""
        if self._sandbox_dir is None:
            return

        all_tools = list(self.fixture_env.tools) + list(self.sca_tool.tools)

        all_env_vars = dict(self.fixture_env.env_vars)
        all_env_vars.update(self.sca_tool.env_vars)

        task_command = self.sca_tool.command.format(
            output_path=str(self.output_path),
            project_dir=str(self.project_dir),
        )

        content = generate_mise_toml(
            tools=all_tools,
            env_vars=all_env_vars if all_env_vars else None,
            task_name="sca",
            task_command=task_command,
        )

        mise_toml_path = self._sandbox_dir / "mise.toml"
        mise_toml_path.write_text(content)

    def _copy_fixture_files(self) -> None:
        """Copy fixture project files to sandbox."""
        if self._sandbox_dir is None:
            return

        self.project_dir.mkdir(parents=True, exist_ok=True)

        src_dir = self.fixture.project_dir
        for item in src_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, self.project_dir / item.name)
            elif item.is_dir():
                shutil.copytree(item, self.project_dir / item.name)
