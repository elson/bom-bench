"""Integration tests for CLI."""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from bom_bench.cli import BomBenchCLI, cli, run


class TestClickCLI:
    """Test Click CLI interface."""

    @pytest.fixture
    def runner(self):
        """Create Click CLI runner."""
        return CliRunner()

    def test_cli_help(self, runner):
        """Test main CLI help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Generate package manager manifests" in result.output

    def test_run_command_help(self, runner):
        """Test run command help."""
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "Generate manifests and lock files" in result.output

    def test_package_managers_flag(self, runner):
        """Test --package-managers flag."""
        result = runner.invoke(run, ["--help"])
        assert "--package-managers" in result.output or "--pm" in result.output

    def test_scenarios_flag(self, runner):
        """Test --scenarios flag."""
        result = runner.invoke(run, ["--help"])
        assert "--scenarios" in result.output

    def test_verbose_flag(self, runner):
        """Test --verbose flag on main CLI (universal option)."""
        result = runner.invoke(cli, ["--help"])
        assert "--verbose" in result.output or "-v" in result.output

    def test_quiet_flag(self, runner):
        """Test --quiet flag on main CLI (universal option)."""
        result = runner.invoke(cli, ["--help"])
        assert "--quiet" in result.output or "-q" in result.output


class TestUniversalLoggingOptions:
    """Test that logging options are universal (apply to all commands)."""

    @pytest.fixture
    def runner(self):
        """Create Click CLI runner."""
        return CliRunner()

    def test_verbose_on_main_cli(self, runner):
        """Test --verbose is available on main CLI group."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "--verbose" in result.output or "-v" in result.output

    def test_quiet_on_main_cli(self, runner):
        """Test --quiet is available on main CLI group."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "--quiet" in result.output or "-q" in result.output

    def test_log_level_on_main_cli(self, runner):
        """Test --log-level is available on main CLI group."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "--log-level" in result.output

    def test_verbose_before_subcommand(self, runner):
        """Test --verbose works before subcommand."""
        result = runner.invoke(cli, ["--verbose", "list-tools"])
        # Should not fail with "no such option"
        assert "no such option" not in result.output.lower()
        assert "Error: No such option" not in result.output

    def test_quiet_before_subcommand(self, runner):
        """Test --quiet works before subcommand."""
        result = runner.invoke(cli, ["--quiet", "list-tools"])
        assert "no such option" not in result.output.lower()
        assert "Error: No such option" not in result.output

    def test_log_level_before_subcommand(self, runner):
        """Test --log-level works before subcommand."""
        result = runner.invoke(cli, ["--log-level", "DEBUG", "list-tools"])
        assert "no such option" not in result.output.lower()
        assert "Error: No such option" not in result.output

    def test_mutually_exclusive_options(self, runner):
        """Test that --verbose, --quiet, and --log-level are mutually exclusive."""
        result = runner.invoke(cli, ["--verbose", "--quiet", "list-tools"])
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower() or "exclusive" in result.output.lower()

    def test_log_level_flag(self, runner):
        """Test --log-level flag on main CLI."""
        result = runner.invoke(cli, ["--help"])
        assert "--log-level" in result.output

    def test_mutually_exclusive_logging(self, runner):
        """Test that verbose and quiet are mutually exclusive on main CLI."""
        result = runner.invoke(cli, ["-v", "-q", "list-tools"])
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_clean_command_stub(self, runner):
        """Test clean command is available but not implemented."""
        result = runner.invoke(cli, ["clean", "--help"])
        assert result.exit_code == 0
        assert "Clean output directory" in result.output

    def test_validate_command_stub(self, runner):
        """Test validate command is available but not implemented."""
        result = runner.invoke(cli, ["validate", "--help"])
        assert result.exit_code == 0
        assert "Validate SBOM file" in result.output

    def test_info_command_stub(self, runner):
        """Test info command is available but not implemented."""
        result = runner.invoke(cli, ["info", "--help"])
        assert result.exit_code == 0
        assert "Show configuration" in result.output


class TestPackageManagerParsing:
    """Test package manager parsing logic."""

    @pytest.fixture
    def cli(self):
        """Create CLI instance."""
        return BomBenchCLI()

    def test_parse_single_pm(self, cli):
        """Test parsing single package manager."""
        pms = cli.parse_package_managers("uv")
        assert pms == ["uv"]

    def test_parse_multiple_pms(self, cli):
        """Test parsing multiple package managers."""
        # Note: pip not yet implemented, so test with just uv for now
        # When pip is added, update to: pms = cli.parse_package_managers("uv,pip")
        pms = cli.parse_package_managers("uv")
        assert pms == ["uv"]

    def test_parse_all_pms(self, cli):
        """Test parsing 'all' keyword."""
        pms = cli.parse_package_managers("all")
        assert isinstance(pms, list)
        assert "uv" in pms

    def test_parse_invalid_pm(self, cli):
        """Test parsing invalid package manager."""
        with pytest.raises(ValueError, match="Unknown package manager"):
            cli.parse_package_managers("invalid")

    def test_parse_pm_with_spaces(self, cli):
        """Test parsing package managers with spaces (tests trimming)."""
        # Test that spaces are properly trimmed
        pms = cli.parse_package_managers(" uv ")
        assert pms == ["uv"]


class TestScenarioFiltering:
    """Test scenario filtering logic."""

    @pytest.fixture
    def cli(self):
        """Create CLI instance."""
        return BomBenchCLI()

    def test_create_default_filter(self, cli):
        """Test creating default filter."""
        filter_config = cli.create_filter()
        assert filter_config.universal_only is True
        assert "example" in filter_config.exclude_patterns

    def test_create_filter_no_universal(self, cli):
        """Test creating filter without universal requirement."""
        filter_config = cli.create_filter(universal_only=False)
        assert filter_config.universal_only is False

    def test_filter_by_names(self, cli):
        """Test filtering scenarios by specific names."""
        from bom_bench.models.scenario import Scenario, Root, ResolverOptions

        scenarios = [
            Scenario(
                name="scenario-1",
                root=Root(),
                resolver_options=ResolverOptions(),
            ),
            Scenario(
                name="scenario-2",
                root=Root(),
                resolver_options=ResolverOptions(),
            ),
            Scenario(
                name="scenario-3",
                root=Root(),
                resolver_options=ResolverOptions(),
            ),
        ]

        filtered = cli.filter_by_names(scenarios, ["scenario-1", "scenario-3"])
        assert len(filtered) == 2
        assert filtered[0].name == "scenario-1"
        assert filtered[1].name == "scenario-3"


class TestCLIProcessing:
    """Test CLI processing logic."""

    @pytest.fixture
    def cli(self):
        """Create CLI instance."""
        return BomBenchCLI()

    def test_process_scenario_success(self, cli):
        """Test successful scenario processing."""
        from bom_bench.models.scenario import (
            Scenario,
            Root,
            Requirement,
            ResolverOptions,
        )
        from bom_bench.models.result import ProcessingStatus

        scenario = Scenario(
            name="test-scenario",
            root=Root(
                requires=[Requirement(requirement="package-a>=1.0.0")],
                requires_python=">=3.12",
            ),
            resolver_options=ResolverOptions(universal=True),
            source="packse",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_base = Path(tmpdir)

            result = cli.process_scenario(scenario, "uv", output_base)

            assert result.status == ProcessingStatus.SUCCESS
            assert result.scenario_name == "test-scenario"
            assert result.package_manager == "uv"
            assert result.output_dir is not None
            assert result.output_dir.exists()

            # Check that pyproject.toml was created in assets subdirectory
            pyproject = result.output_dir / "assets" / "pyproject.toml"
            assert pyproject.exists()

    def test_process_scenario_incompatible(self, cli):
        """Test processing incompatible scenario."""
        from bom_bench.models.scenario import Scenario, Root, ResolverOptions
        from bom_bench.models.result import ProcessingStatus

        scenario = Scenario(
            name="test-scenario",
            root=Root(),
            resolver_options=ResolverOptions(),
            source="other-source",  # UV doesn't support this
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_base = Path(tmpdir)

            result = cli.process_scenario(scenario, "uv", output_base)

            assert result.status == ProcessingStatus.SKIPPED
            assert "not compatible" in result.error_message.lower()

    def test_process_scenario_invalid_pm(self, cli):
        """Test processing with invalid package manager."""
        from bom_bench.models.scenario import Scenario, Root, ResolverOptions
        from bom_bench.models.result import ProcessingStatus

        scenario = Scenario(
            name="test-scenario",
            root=Root(),
            resolver_options=ResolverOptions(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_base = Path(tmpdir)

            result = cli.process_scenario(scenario, "invalid-pm", output_base)

            assert result.status == ProcessingStatus.FAILED
            assert "not installed" in result.error_message.lower()


class TestSBOMGeneration:
    """Test SBOM generation in CLI."""

    @pytest.fixture
    def cli(self):
        """Create CLI instance."""
        return BomBenchCLI()

    def test_sbom_generated_from_lock_file(self, cli):
        """Test that SBOM is generated from lock file after successful locking."""
        from bom_bench.models.scenario import (
            Scenario,
            Root,
            Requirement,
            ResolverOptions,
        )
        from bom_bench.models.result import ProcessingStatus, LockResult, LockStatus
        from bom_bench.generators.sbom.cyclonedx import generate_cyclonedx_sbom
        from bom_bench.models.scenario import ExpectedPackage

        # Create minimal scenario
        scenario = Scenario(
            name="test-scenario",
            root=Root(
                requires=[Requirement(requirement="package-a>=1.0.0")],
                requires_python=">=3.12",
            ),
            resolver_options=ResolverOptions(universal=True),
            source="packse",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_base = Path(tmpdir)
            output_dir = output_base / "scenarios" / "uv" / "test-scenario"
            assets_dir = output_dir / "assets"
            assets_dir.mkdir(parents=True)

            # Create a mock lock file in assets subdirectory
            lock_content = """version = 1
requires-python = ">=3.12"

[[package]]
name = "project"
version = "0.1.0"
source = { virtual = "." }

[[package]]
name = "package-a"
version = "1.0.0"

[[package]]
name = "package-b"
version = "2.0.0"
"""
            lock_file = assets_dir / "uv.lock"
            lock_file.write_text(lock_content)

            # Generate SBOM from the lock file using plugin API
            from bom_bench.package_managers import pm_generate_sbom_for_lock

            # Create mock successful lock result
            lock_result = LockResult(
                scenario_name=scenario.name,
                package_manager="uv",
                status=LockStatus.SUCCESS,
                exit_code=0,
                stdout="Resolved 2 packages",
                stderr="",
                lock_file=lock_file,
                duration_seconds=0.1
            )

            sbom_path = pm_generate_sbom_for_lock("uv", scenario, output_dir, lock_result)

            assert sbom_path is not None
            assert sbom_path.exists()

            # Verify SBOM is pure CycloneDX (no wrapper)
            import json
            with open(sbom_path) as f:
                sbom = json.load(f)

            # Top-level should be CycloneDX fields directly
            assert sbom["bomFormat"] == "CycloneDX"
            assert len(sbom["components"]) == 2

            # Check that packages from lock file are in SBOM
            component_names = {comp["name"] for comp in sbom["components"]}
            assert "package-a" in component_names
            assert "package-b" in component_names

            # Verify meta.json was also created
            meta_path = output_dir / "meta.json"
            assert meta_path.exists()

            with open(meta_path) as f:
                meta = json.load(f)

            assert meta["satisfiable"] is True
            assert meta["package_manager_result"]["exit_code"] == 0

    def test_sbom_result_on_lock_failure(self, cli):
        """Test that meta.json is generated with satisfiable=false when lock fails."""
        from bom_bench.models.scenario import (
            Scenario,
            Root,
            Requirement,
            ResolverOptions,
        )
        from bom_bench.models.result import LockResult, LockStatus

        scenario = Scenario(
            name="test-scenario",
            root=Root(
                requires=[Requirement(requirement="package-a>=1.0.0")],
                requires_python=">=3.12",
            ),
            resolver_options=ResolverOptions(universal=True),
            source="packse",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "test-output"
            output_dir.mkdir()

            # Create mock failed lock result (no lock file) using plugin API
            from bom_bench.package_managers import pm_generate_sbom_for_lock

            lock_result = LockResult(
                scenario_name=scenario.name,
                package_manager="uv",
                status=LockStatus.FAILED,
                exit_code=1,
                stdout="",
                stderr="No solution found",
                lock_file=None,
                duration_seconds=0.1
            )

            result_path = pm_generate_sbom_for_lock("uv", scenario, output_dir, lock_result)

            # Should generate meta.json (not SBOM since lock failed)
            assert result_path is not None
            assert result_path.exists()

            # Verify meta.json structure
            import json
            meta_path = output_dir / "meta.json"
            assert meta_path.exists()

            with open(meta_path) as f:
                meta = json.load(f)

            # Check that satisfiable is false
            assert meta["satisfiable"] is False
            assert meta["package_manager_result"]["exit_code"] == 1
            assert meta["package_manager_result"]["stderr"] == "No solution found"

            # SBOM should not exist for failed lock
            sbom_path = output_dir / "expected.cdx.json"
            assert not sbom_path.exists()

    def test_sbom_file_structure(self, cli):
        """Test the structure of generated SBOM file."""
        from bom_bench.models.scenario import (
            Scenario,
            Root,
            Requirement,
            ResolverOptions,
        )
        from bom_bench.models.result import LockResult, LockStatus

        scenario = Scenario(
            name="test-sbom",
            root=Root(
                requires=[Requirement(requirement="requests>=2.0.0")],
                requires_python=">=3.8",
            ),
            resolver_options=ResolverOptions(universal=True),
            source="packse",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "test-output"
            assets_dir = output_dir / "assets"
            assets_dir.mkdir(parents=True)

            # Create a mock lock file in assets subdirectory
            lock_content = """version = 1
requires-python = ">=3.8"

[[package]]
name = "project"
version = "0.1.0"
source = { virtual = "." }

[[package]]
name = "requests"
version = "2.31.0"
"""
            lock_file = assets_dir / "uv.lock"
            lock_file.write_text(lock_content)

            # Generate SBOM using plugin API
            from bom_bench.package_managers import pm_generate_sbom_for_lock

            # Create mock successful lock result
            lock_result = LockResult(
                scenario_name=scenario.name,
                package_manager="uv",
                status=LockStatus.SUCCESS,
                exit_code=0,
                stdout="Resolved 1 package",
                stderr="",
                lock_file=lock_file,
                duration_seconds=0.1
            )

            sbom_path = pm_generate_sbom_for_lock("uv", scenario, output_dir, lock_result)

            assert sbom_path.exists()

            # Verify SBOM is pure CycloneDX (no wrapper)
            import json
            with open(sbom_path) as f:
                sbom = json.load(f)

            # Check top-level CycloneDX fields
            assert "bomFormat" in sbom
            assert "specVersion" in sbom
            assert "metadata" in sbom
            assert "components" in sbom

            # Check metadata
            assert sbom["metadata"]["component"]["name"] == "test-sbom"
            assert sbom["metadata"]["component"]["type"] == "application"

            # Check component structure
            assert len(sbom["components"]) == 1
            component = sbom["components"][0]
            assert component["type"] == "library"
            assert component["name"] == "requests"
            assert component["version"] == "2.31.0"
            assert component["purl"] == "pkg:pypi/requests@2.31.0"

            # Verify meta.json was created
            meta_path = output_dir / "meta.json"
            assert meta_path.exists()

            with open(meta_path) as f:
                meta = json.load(f)

            assert meta["satisfiable"] is True
