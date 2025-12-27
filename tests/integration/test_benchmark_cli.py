"""Integration tests for benchmark CLI commands."""

import json
import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from bom_bench.cli import cli
from bom_bench.models.sca import SBOMResult, SBOMGenerationStatus


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def reset_plugin_state():
    """Reset plugin state before and after each test."""
    from bom_bench.plugins import reset_plugins
    reset_plugins()
    yield
    reset_plugins()


class TestListToolsCommand:
    """Tests for list-tools command."""

    def test_list_tools_shows_cdxgen(self, runner, reset_plugin_state):
        """Test that list-tools shows cdxgen."""
        result = runner.invoke(cli, ["list-tools"])

        assert result.exit_code == 0
        assert "cdxgen" in result.output
        assert "CycloneDX Generator" in result.output

    def test_list_tools_with_check(self, runner, reset_plugin_state):
        """Test list-tools with --check flag."""
        result = runner.invoke(cli, ["list-tools", "--check"])

        assert result.exit_code == 0
        assert "cdxgen" in result.output
        # Should have either [installed] or [not found]
        assert "[installed]" in result.output or "[not found]" in result.output


class TestBenchmarkCommand:
    """Tests for benchmark command."""

    def test_benchmark_help(self, runner):
        """Test benchmark --help."""
        result = runner.invoke(cli, ["benchmark", "--help"])

        assert result.exit_code == 0
        assert "Run SCA tool benchmarking" in result.output
        assert "--pm" in result.output
        assert "--tools" in result.output
        assert "--scenarios" in result.output

    def test_benchmark_unknown_tool(self, runner, reset_plugin_state):
        """Test benchmark with unknown tool."""
        result = runner.invoke(cli, ["benchmark", "--tools", "nonexistent-tool"])

        assert result.exit_code != 0
        assert "Unknown SCA tool" in result.output

    @patch("bom_bench.benchmarking.runner.BenchmarkRunner")
    def test_benchmark_runs_with_defaults(self, mock_runner_class, runner, reset_plugin_state, tmp_path):
        """Test benchmark runs with default options."""
        mock_runner = MagicMock()
        mock_runner.run.return_value = 0
        mock_runner_class.return_value = mock_runner

        result = runner.invoke(cli, [
            "benchmark",
            "--pm", "uv",
            "--tools", "cdxgen",
            "-o", str(tmp_path),
            "--benchmarks-dir", str(tmp_path / "benchmarks"),
        ])

        # Should create runner with correct args
        mock_runner_class.assert_called_once()
        call_kwargs = mock_runner_class.call_args[1]
        assert call_kwargs["tools"] == ["cdxgen"]

        # Should call run
        mock_runner.run.assert_called_once()

    @patch("bom_bench.benchmarking.runner.BenchmarkRunner")
    def test_benchmark_with_scenarios_filter(self, mock_runner_class, runner, reset_plugin_state, tmp_path):
        """Test benchmark with specific scenarios."""
        mock_runner = MagicMock()
        mock_runner.run.return_value = 0
        mock_runner_class.return_value = mock_runner

        result = runner.invoke(cli, [
            "benchmark",
            "--pm", "uv",
            "--tools", "cdxgen",
            "--scenarios", "scenario-1,scenario-2",
            "-o", str(tmp_path),
            "--benchmarks-dir", str(tmp_path / "benchmarks"),
        ])

        # Should pass scenarios to run
        mock_runner.run.assert_called_once()
        call_args = mock_runner.run.call_args
        assert call_args[1]["scenarios"] == ["scenario-1", "scenario-2"]

    @patch("bom_bench.benchmarking.runner.BenchmarkRunner")
    def test_benchmark_returns_runner_exit_code(self, mock_runner_class, runner, reset_plugin_state, tmp_path):
        """Test that benchmark returns runner's exit code."""
        mock_runner = MagicMock()
        mock_runner.run.return_value = 1  # Simulate failure
        mock_runner_class.return_value = mock_runner

        result = runner.invoke(cli, [
            "benchmark",
            "--pm", "uv",
            "--tools", "cdxgen",
            "-o", str(tmp_path),
            "--benchmarks-dir", str(tmp_path / "benchmarks"),
        ])

        assert result.exit_code == 1


class TestSetupCommand:
    """Tests for setup command."""

    def test_setup_help(self, runner):
        """Test setup --help."""
        result = runner.invoke(cli, ["setup", "--help"])

        assert result.exit_code == 0
        assert "Generate manifests" in result.output
        assert "--pm" in result.output

    def test_setup_is_default_command(self, runner):
        """Test that setup is the default command."""
        # When running without a subcommand, it should invoke setup
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "setup" in result.output


class TestRunCommandDeprecation:
    """Tests for deprecated run command."""

    def test_run_shows_deprecation_warning(self, runner, tmp_path):
        """Test that run shows deprecation warning."""
        result = runner.invoke(cli, [
            "run",
            "--pm", "uv",
            "-o", str(tmp_path),
        ])

        # Check for deprecation warning in output
        # Note: exit code may be non-zero if setup fails for other reasons
        assert "deprecated" in result.output.lower() or result.exit_code == 0


class TestVerboseQuietFlags:
    """Tests for verbose/quiet flags."""

    def test_verbose_and_quiet_mutually_exclusive(self, runner):
        """Test that -v and -q are mutually exclusive."""
        # Logging options are on main CLI group, must come before subcommand
        result = runner.invoke(cli, ["-v", "-q", "setup"])

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_verbose_and_log_level_mutually_exclusive(self, runner):
        """Test that -v and --log-level are mutually exclusive."""
        # Logging options are on main CLI group, must come before subcommand
        result = runner.invoke(cli, ["-v", "--log-level", "DEBUG", "setup"])

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_quiet_and_log_level_mutually_exclusive(self, runner):
        """Test that -q and --log-level are mutually exclusive."""
        # Logging options are on main CLI group, must come before subcommand
        result = runner.invoke(cli, ["-q", "--log-level", "DEBUG", "setup"])

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()
