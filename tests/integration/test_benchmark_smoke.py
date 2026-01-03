"""End-to-end smoke test for benchmark functionality.

This test verifies that the core benchmark workflow works:
1. Load fixtures from cache
2. Run SCA tool in sandbox
3. Generate SBOM
4. Compare with expected SBOM
5. Calculate metrics
6. Write output files

This would catch issues like:
- Sandbox cleanup timing bugs
- File I/O problems
- Plugin loading failures
- SBOM parsing errors
"""

import json
from pathlib import Path

import pytest

from bom_bench.plugins import initialize_plugins
from bom_bench.runner import BenchmarkRunner


@pytest.fixture(scope="module")
def initialized_plugins():
    """Initialize plugins once for all tests in this module."""
    initialize_plugins()


class TestBenchmarkSmoke:
    """Smoke tests for end-to-end benchmark functionality."""

    def test_benchmark_single_fixture_cdxgen(self, initialized_plugins, tmp_path: Path):
        """Run benchmark on a single fixture with cdxgen.

        This is a smoke test to verify basic functionality works end-to-end.
        Uses cached packse fixtures, so no packse server required.
        """
        # Create runner with temp output directory
        output_dir = tmp_path / "benchmarks"
        runner = BenchmarkRunner(output_dir=output_dir)

        # Run benchmark on single fixture
        summaries = runner.run(
            tools=["cdxgen"],
            fixtures=["fork-basic"],  # Simple fixture with 2 dependencies
        )

        # Verify we got results
        assert len(summaries) == 1, "Should have exactly one summary (cdxgen x packse)"

        summary = summaries[0]
        assert summary.tool_name == "cdxgen"
        assert summary.package_manager == "packse"
        assert summary.total_scenarios == 1

        # Verify benchmark succeeded
        assert summary.successful == 1, "Benchmark should succeed"
        assert summary.sbom_failed == 0, "Should have no SBOM generation failures"
        assert summary.parse_errors == 0, "Should have no parse errors"

        # Verify metrics are reasonable
        assert summary.mean_precision is not None
        assert summary.mean_recall is not None
        assert summary.mean_f1_score is not None
        assert 0.0 <= summary.mean_precision <= 1.0
        assert 0.0 <= summary.mean_recall <= 1.0
        assert 0.0 <= summary.mean_f1_score <= 1.0

        # Verify output file was created
        expected_output = output_dir / "cdxgen" / "packse" / "fork-basic" / "actual.cdx.json"
        assert expected_output.exists(), f"Output SBOM should exist at {expected_output}"

        # Verify output file is valid JSON and has expected structure
        with open(expected_output) as f:
            sbom = json.load(f)

        assert sbom.get("bomFormat") == "CycloneDX"
        assert "components" in sbom
        assert isinstance(sbom["components"], list)

    def test_benchmark_single_fixture_syft(self, initialized_plugins, tmp_path: Path):
        """Run benchmark on a single fixture with syft.

        Tests with a different SCA tool to verify tool-agnostic functionality.
        """
        output_dir = tmp_path / "benchmarks"
        runner = BenchmarkRunner(output_dir=output_dir)

        summaries = runner.run(
            tools=["syft"],
            fixtures=["fork-basic"],
        )

        assert len(summaries) == 1
        summary = summaries[0]
        assert summary.tool_name == "syft"
        assert summary.total_scenarios == 1

        # Syft should also succeed
        assert summary.successful == 1, "Benchmark should succeed"

        # Verify output file
        expected_output = output_dir / "syft" / "packse" / "fork-basic" / "actual.cdx.json"
        assert expected_output.exists()

        with open(expected_output) as f:
            sbom = json.load(f)
        assert sbom.get("bomFormat") == "CycloneDX"

    def test_benchmark_unsatisfiable_fixture(self, initialized_plugins, tmp_path: Path):
        """Run benchmark on an unsatisfiable fixture.

        Verifies that unsatisfiable scenarios are handled correctly.
        """
        output_dir = tmp_path / "benchmarks"
        runner = BenchmarkRunner(output_dir=output_dir)

        # Use a fixture known to be unsatisfiable
        summaries = runner.run(
            tools=["cdxgen"],
            fixtures=["fork-conflict-unsatisfiable"],
        )

        assert len(summaries) == 1
        summary = summaries[0]

        # Should be marked as unsatisfiable, not a failure
        assert summary.total_scenarios == 1
        assert summary.unsatisfiable == 1
        assert summary.successful == 0
        assert summary.sbom_failed == 0

    def test_benchmark_multiple_fixtures(self, initialized_plugins, tmp_path: Path):
        """Run benchmark on multiple fixtures.

        Verifies that running multiple fixtures works correctly.
        """
        output_dir = tmp_path / "benchmarks"
        runner = BenchmarkRunner(output_dir=output_dir)

        summaries = runner.run(
            tools=["cdxgen"],
            fixtures=["fork-basic", "fork-marker-selection"],
        )

        assert len(summaries) == 1
        summary = summaries[0]
        assert summary.total_scenarios == 2
        assert summary.successful >= 1, "At least one fixture should succeed"

        # Verify both output files exist
        fork_basic_output = output_dir / "cdxgen" / "packse" / "fork-basic" / "actual.cdx.json"
        fork_marker_output = (
            output_dir / "cdxgen" / "packse" / "fork-marker-selection" / "actual.cdx.json"
        )

        assert fork_basic_output.exists()
        assert fork_marker_output.exists()
