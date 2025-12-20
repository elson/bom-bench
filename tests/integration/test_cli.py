"""Integration tests for CLI."""

import tempfile
from pathlib import Path

import pytest

from bom_bench.cli import BomBenchCLI


class TestCLIParsing:
    """Test CLI argument parsing."""

    @pytest.fixture
    def cli(self):
        """Create CLI instance."""
        return BomBenchCLI()

    def test_parse_default_args(self, cli):
        """Test parsing with no arguments."""
        args = cli.parse_args([])
        assert args.package_managers == "uv"
        assert args.lock is False
        assert args.scenarios is None
        assert args.no_universal_filter is False

    def test_parse_lock_flag(self, cli):
        """Test parsing --lock flag."""
        args = cli.parse_args(["--lock"])
        assert args.lock is True

    def test_parse_package_managers(self, cli):
        """Test parsing --package-managers flag."""
        args = cli.parse_args(["--package-managers", "uv,pip"])
        assert args.package_managers == "uv,pip"

    def test_parse_scenarios(self, cli):
        """Test parsing --scenarios flag."""
        args = cli.parse_args(["--scenarios", "fork-basic,local-simple"])
        assert args.scenarios == "fork-basic,local-simple"

    def test_parse_output_dir(self, cli):
        """Test parsing --output-dir flag."""
        args = cli.parse_args(["--output-dir", "/tmp/test"])
        assert args.output_dir == Path("/tmp/test")

    def test_parse_no_universal_filter(self, cli):
        """Test parsing --no-universal-filter flag."""
        args = cli.parse_args(["--no-universal-filter"])
        assert args.no_universal_filter is True


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

            # Check that pyproject.toml was created
            pyproject = result.output_dir / "pyproject.toml"
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
            assert "not found" in result.error_message.lower()
