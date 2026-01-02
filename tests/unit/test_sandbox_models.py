from pathlib import Path

from bom_bench.models.sandbox import SandboxConfig, SandboxResult


class TestSandboxConfig:
    def test_default_config(self):
        config = SandboxConfig()
        assert config.temp_dir is None
        assert config.keep_on_success is False
        assert config.keep_on_failure is True
        assert config.timeout == 120

    def test_custom_config(self, tmp_path: Path):
        config = SandboxConfig(
            temp_dir=tmp_path,
            keep_on_success=True,
            keep_on_failure=False,
            timeout=60,
        )
        assert config.temp_dir == tmp_path
        assert config.keep_on_success is True
        assert config.keep_on_failure is False
        assert config.timeout == 60


class TestSandboxResult:
    def test_successful_result(self, tmp_path: Path):
        sbom_path = tmp_path / "actual.cdx.json"

        result = SandboxResult(
            fixture_name="fork-basic",
            tool_name="cdxgen",
            success=True,
            actual_sbom_path=sbom_path,
            duration_seconds=1.5,
            exit_code=0,
            stdout="Generated SBOM",
            stderr="",
        )

        assert result.success is True
        assert result.fixture_name == "fork-basic"
        assert result.tool_name == "cdxgen"
        assert result.actual_sbom_path == sbom_path
        assert result.exit_code == 0
        assert result.error_message is None

    def test_failed_result(self):
        result = SandboxResult(
            fixture_name="broken-fixture",
            tool_name="syft",
            success=False,
            duration_seconds=0.5,
            exit_code=1,
            stdout="",
            stderr="Error: could not parse",
            error_message="Tool failed with exit code 1",
        )

        assert result.success is False
        assert result.actual_sbom_path is None
        assert result.exit_code == 1
        assert result.error_message == "Tool failed with exit code 1"

    def test_timeout_result(self):
        result = SandboxResult(
            fixture_name="slow-fixture",
            tool_name="cdxgen",
            success=False,
            duration_seconds=120.0,
            exit_code=None,
            stdout="",
            stderr="",
            error_message="Timeout after 120 seconds",
        )

        assert result.success is False
        assert result.exit_code is None
        assert result.error_message == "Timeout after 120 seconds"

    def test_result_with_preserved_sandbox(self, tmp_path: Path):
        sandbox_dir = tmp_path / "sandbox-123"

        result = SandboxResult(
            fixture_name="debug-fixture",
            tool_name="cdxgen",
            success=False,
            duration_seconds=0.5,
            exit_code=1,
            stdout="",
            stderr="Error",
            sandbox_dir=sandbox_dir,
        )

        assert result.sandbox_dir == sandbox_dir

    def test_result_defaults(self):
        result = SandboxResult(
            fixture_name="test",
            tool_name="test-tool",
            success=True,
        )

        assert result.actual_sbom_path is None
        assert result.duration_seconds == 0.0
        assert result.exit_code is None
        assert result.stdout == ""
        assert result.stderr == ""
        assert result.error_message is None
        assert result.sandbox_dir is None
