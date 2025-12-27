"""End-to-end tests for the benchmark workflow.

These tests validate the complete setup → benchmark workflow.
They require cdxgen to be installed.
"""

import json
import shutil
import pytest
from pathlib import Path

from bom_bench.plugins import reset_plugins


@pytest.fixture(autouse=True)
def reset_plugin_state():
    """Reset plugin state before and after each test."""
    reset_plugins()
    yield
    reset_plugins()


def cdxgen_available():
    """Check if cdxgen is available."""
    return shutil.which("cdxgen") is not None


@pytest.mark.skipif(not cdxgen_available(), reason="cdxgen not installed")
class TestE2EBenchmarkWorkflow:
    """End-to-end tests for the complete benchmark workflow."""

    def test_benchmark_single_scenario(self, tmp_path):
        """Test complete setup → benchmark workflow for a single scenario."""
        from bom_bench.benchmarking.runner import BenchmarkRunner
        from bom_bench.plugins import initialize_plugins

        # Create a mock project with expected SBOM
        output_dir = tmp_path / "output"
        benchmarks_dir = tmp_path / "benchmarks"

        # Create a minimal Python project
        scenario_dir = output_dir / "uv" / "test-scenario"
        scenario_dir.mkdir(parents=True)

        # Create pyproject.toml
        pyproject = scenario_dir / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
version = "0.1.0"
dependencies = []
requires-python = ">=3.12"
""")

        # Create expected SBOM (empty, matching an empty project)
        expected_sbom = scenario_dir / "expected.cdx.json"
        expected_sbom.write_text(json.dumps({
            "satisfiable": True,
            "sbom": {
                "bomFormat": "CycloneDX",
                "specVersion": "1.6",
                "components": []
            }
        }))

        # Initialize plugins and run benchmark
        initialize_plugins()

        runner = BenchmarkRunner(
            output_dir=output_dir,
            benchmarks_dir=benchmarks_dir,
            tools=["cdxgen"]
        )

        exit_code = runner.run(package_managers="uv")

        # Check that benchmark ran
        # Note: exit_code may be 0 or 1 depending on cdxgen's behavior
        # The important thing is that outputs were created

        # Verify output structure
        result_dir = benchmarks_dir / "cdxgen" / "uv" / "test-scenario"
        assert result_dir.exists(), f"Result directory not created: {result_dir}"

        # Check that actual SBOM was created
        actual_sbom = result_dir / "actual.cdx.json"
        # cdxgen might succeed or fail depending on the project, but it should try

        # Check result.json was created
        result_json = result_dir / "result.json"
        assert result_json.exists(), "result.json not created"

        with open(result_json) as f:
            result = json.load(f)

        assert result["scenario_name"] == "test-scenario"
        assert result["package_manager"] == "uv"
        assert result["tool_name"] == "cdxgen"
        assert "status" in result

        # Check summary.json was created
        summary_json = benchmarks_dir / "cdxgen" / "uv" / "summary.json"
        assert summary_json.exists(), "summary.json not created"

        with open(summary_json) as f:
            summary = json.load(f)

        assert summary["tool_name"] == "cdxgen"
        assert summary["package_manager"] == "uv"
        assert summary["total_scenarios"] == 1

        # Check CSV was created
        results_csv = benchmarks_dir / "cdxgen" / "uv" / "results.csv"
        assert results_csv.exists(), "results.csv not created"

    def test_benchmark_with_dependencies(self, tmp_path):
        """Test benchmark with a project that has actual dependencies."""
        from bom_bench.benchmarking.runner import BenchmarkRunner
        from bom_bench.plugins import initialize_plugins

        output_dir = tmp_path / "output"
        benchmarks_dir = tmp_path / "benchmarks"

        # Create a project with known dependencies
        scenario_dir = output_dir / "uv" / "deps-scenario"
        scenario_dir.mkdir(parents=True)

        # Create pyproject.toml with a dependency
        pyproject = scenario_dir / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
version = "0.1.0"
dependencies = ["click>=8.0.0"]
requires-python = ">=3.12"
""")

        # Create expected SBOM with click
        expected_sbom = scenario_dir / "expected.cdx.json"
        expected_sbom.write_text(json.dumps({
            "satisfiable": True,
            "sbom": {
                "bomFormat": "CycloneDX",
                "specVersion": "1.6",
                "components": [
                    {
                        "type": "library",
                        "name": "click",
                        "version": "8.1.7",
                        "purl": "pkg:pypi/click@8.1.7"
                    }
                ]
            }
        }))

        # Initialize and run
        initialize_plugins()

        runner = BenchmarkRunner(
            output_dir=output_dir,
            benchmarks_dir=benchmarks_dir,
            tools=["cdxgen"]
        )

        exit_code = runner.run(package_managers="uv")

        # Verify result was created
        result_json = benchmarks_dir / "cdxgen" / "uv" / "deps-scenario" / "result.json"
        assert result_json.exists()

        with open(result_json) as f:
            result = json.load(f)

        # Should have run (regardless of success/failure)
        assert result["scenario_name"] == "deps-scenario"
        assert "status" in result


class TestPluginSystem:
    """Tests for the plugin system itself."""

    def test_cdxgen_plugin_registers(self):
        """Test that cdxgen plugin registers correctly."""
        from bom_bench.plugins import initialize_plugins, get_registered_tools

        initialize_plugins()
        tools = get_registered_tools()

        assert "cdxgen" in tools
        assert tools["cdxgen"].name == "cdxgen"
        assert "python" in tools["cdxgen"].supported_ecosystems

    def test_plugin_availability_check(self):
        """Test tool availability check."""
        from bom_bench.plugins import initialize_plugins, check_tool_available

        initialize_plugins()

        # cdxgen availability depends on installation
        result = check_tool_available("cdxgen")
        assert isinstance(result, bool)

        # Unknown tool returns False
        assert check_tool_available("nonexistent-tool") is False

    def test_plugin_list(self):
        """Test listing available tools."""
        from bom_bench.plugins import initialize_plugins, list_available_tools

        initialize_plugins()
        tools = list_available_tools()

        assert "cdxgen" in tools
        assert "syft" in tools

    def test_syft_plugin_registers(self):
        """Test that syft plugin registers correctly."""
        from bom_bench.plugins import initialize_plugins, get_registered_tools

        initialize_plugins()
        tools = get_registered_tools()

        assert "syft" in tools
        assert tools["syft"].name == "syft"
        assert "python" in tools["syft"].supported_ecosystems
        assert tools["syft"].homepage == "https://github.com/anchore/syft"


class TestPurlComparison:
    """Tests for PURL comparison and metrics calculation."""

    def test_perfect_match_metrics(self):
        """Test metrics for perfectly matching SBOMs."""
        from bom_bench.models.sca import PurlMetrics

        expected = {"pkg:pypi/a@1.0.0", "pkg:pypi/b@2.0.0"}
        actual = {"pkg:pypi/a@1.0.0", "pkg:pypi/b@2.0.0"}

        metrics = PurlMetrics.calculate(expected, actual)

        assert metrics.true_positives == 2
        assert metrics.false_positives == 0
        assert metrics.false_negatives == 0
        assert metrics.precision == 1.0
        assert metrics.recall == 1.0
        assert metrics.f1_score == 1.0

    def test_partial_match_metrics(self):
        """Test metrics for partially matching SBOMs."""
        from bom_bench.models.sca import PurlMetrics

        expected = {"pkg:pypi/a@1.0.0", "pkg:pypi/b@2.0.0"}
        actual = {"pkg:pypi/a@1.0.0", "pkg:pypi/c@3.0.0"}

        metrics = PurlMetrics.calculate(expected, actual)

        assert metrics.true_positives == 1  # 'a' matches
        assert metrics.false_positives == 1  # 'c' extra
        assert metrics.false_negatives == 1  # 'b' missing
        assert metrics.precision == 0.5  # 1/2
        assert metrics.recall == 0.5  # 1/2

    def test_purl_normalization(self):
        """Test PURL normalization for comparison."""
        from bom_bench.benchmarking.comparison import normalize_purl

        # PyPI packages are lowercased and underscores converted to hyphens
        assert normalize_purl("pkg:pypi/My_Package@1.0.0") == "pkg:pypi/my-package@1.0.0"

        # Qualifiers are removed
        assert "?" not in normalize_purl("pkg:pypi/pkg@1.0.0?vcs_url=...")
