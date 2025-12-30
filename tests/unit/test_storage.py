"""Tests for benchmark result storage and export."""

import csv
import json
from pathlib import Path

from bom_bench.benchmarking.storage import (
    export_benchmark_csv,
    save_benchmark_result,
    save_benchmark_summary,
)
from bom_bench.models.sca_tool import (
    BenchmarkResult,
    BenchmarkStatus,
    BenchmarkSummary,
    PurlMetrics,
    ScanResult,
    ScanStatus,
)


class TestSaveBenchmarkResult:
    """Tests for saving individual benchmark results."""

    def test_save_successful_result(self, tmp_path):
        """Test saving a successful benchmark result."""
        output_path = tmp_path / "result.json"

        metrics = PurlMetrics.calculate(
            {"pkg:pypi/a@1.0", "pkg:pypi/b@2.0"}, {"pkg:pypi/a@1.0", "pkg:pypi/b@2.0"}
        )

        result = BenchmarkResult(
            scenario_name="test-scenario",
            package_manager="uv",
            tool_name="cdxgen",
            status=BenchmarkStatus.SUCCESS,
            metrics=metrics,
            expected_sbom_path=Path("/expected.json"),
            actual_sbom_path=Path("/actual.json"),
        )

        save_benchmark_result(result, output_path)

        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)

        assert data["scenario_name"] == "test-scenario"
        assert data["package_manager"] == "uv"
        assert data["tool_name"] == "cdxgen"
        assert data["status"] == "success"
        assert data["metrics"]["precision"] == 1.0
        assert data["metrics"]["recall"] == 1.0

    def test_save_failed_result(self, tmp_path):
        """Test saving a failed benchmark result."""
        output_path = tmp_path / "result.json"

        sbom_result = ScanResult.failed(
            tool_name="cdxgen", error_message="Tool not found", status=ScanStatus.TOOL_NOT_FOUND
        )

        result = BenchmarkResult(
            scenario_name="test-scenario",
            package_manager="uv",
            tool_name="cdxgen",
            status=BenchmarkStatus.SBOM_GENERATION_FAILED,
            sbom_result=sbom_result,
            error_message="SBOM generation failed",
        )

        save_benchmark_result(result, output_path)

        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)

        assert data["status"] == "sbom_failed"
        assert data["error_message"] == "SBOM generation failed"
        assert data["sbom_result"]["status"] == "tool_not_found"

    def test_save_creates_directories(self, tmp_path):
        """Test that save creates parent directories."""
        output_path = tmp_path / "subdir" / "nested" / "result.json"

        result = BenchmarkResult(
            scenario_name="test",
            package_manager="uv",
            tool_name="cdxgen",
            status=BenchmarkStatus.SUCCESS,
        )

        save_benchmark_result(result, output_path)

        assert output_path.exists()


class TestSaveBenchmarkSummary:
    """Tests for saving benchmark summaries."""

    def test_save_summary(self, tmp_path):
        """Test saving a benchmark summary."""
        output_path = tmp_path / "summary.json"

        summary = BenchmarkSummary(
            package_manager="uv",
            tool_name="cdxgen",
        )

        # Add some results
        for i in range(3):
            metrics = PurlMetrics.calculate({f"pkg:pypi/a{i}@1.0"}, {f"pkg:pypi/a{i}@1.0"})
            result = BenchmarkResult(
                scenario_name=f"scenario-{i}",
                package_manager="uv",
                tool_name="cdxgen",
                status=BenchmarkStatus.SUCCESS,
                metrics=metrics,
            )
            summary.add_result(result)

        summary.calculate_aggregates()
        save_benchmark_summary(summary, output_path)

        assert output_path.exists()

        with open(output_path) as f:
            data = json.load(f)

        assert data["package_manager"] == "uv"
        assert data["tool_name"] == "cdxgen"
        assert data["total_scenarios"] == 3
        assert data["status_breakdown"]["successful"] == 3
        assert data["metrics"]["mean_precision"] == 1.0
        assert data["metrics"]["mean_recall"] == 1.0

    def test_save_summary_with_failures(self, tmp_path):
        """Test saving a summary with mixed results."""
        output_path = tmp_path / "summary.json"

        summary = BenchmarkSummary(
            package_manager="uv",
            tool_name="cdxgen",
        )

        # Add success
        summary.add_result(
            BenchmarkResult(
                scenario_name="success",
                package_manager="uv",
                tool_name="cdxgen",
                status=BenchmarkStatus.SUCCESS,
                metrics=PurlMetrics.calculate({"a"}, {"a"}),
            )
        )

        # Add failure
        summary.add_result(
            BenchmarkResult(
                scenario_name="failure",
                package_manager="uv",
                tool_name="cdxgen",
                status=BenchmarkStatus.SBOM_GENERATION_FAILED,
            )
        )

        # Add unsatisfiable
        summary.add_result(
            BenchmarkResult(
                scenario_name="unsatisfiable",
                package_manager="uv",
                tool_name="cdxgen",
                status=BenchmarkStatus.UNSATISFIABLE,
                expected_satisfiable=False,
            )
        )

        summary.calculate_aggregates()
        save_benchmark_summary(summary, output_path)

        with open(output_path) as f:
            data = json.load(f)

        assert data["total_scenarios"] == 3
        assert data["status_breakdown"]["successful"] == 1
        assert data["status_breakdown"]["sbom_failed"] == 1
        assert data["status_breakdown"]["unsatisfiable"] == 1


class TestExportCsv:
    """Tests for CSV export."""

    def test_export_csv_basic(self, tmp_path):
        """Test basic CSV export."""
        output_path = tmp_path / "results.csv"

        results = [
            BenchmarkResult(
                scenario_name="scenario-1",
                package_manager="uv",
                tool_name="cdxgen",
                status=BenchmarkStatus.SUCCESS,
                metrics=PurlMetrics.calculate({"a", "b"}, {"a", "b"}),
                sbom_result=ScanResult.success("cdxgen", Path("/sbom.json"), 1.5, 0),
            ),
            BenchmarkResult(
                scenario_name="scenario-2",
                package_manager="uv",
                tool_name="cdxgen",
                status=BenchmarkStatus.SBOM_GENERATION_FAILED,
                error_message="Tool failed",
            ),
        ]

        export_benchmark_csv(results, output_path)

        assert output_path.exists()

        with open(output_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2

        # Check first row (success)
        assert rows[0]["scenario_name"] == "scenario-1"
        assert rows[0]["status"] == "success"
        assert rows[0]["precision"] == "1.0000"
        assert rows[0]["recall"] == "1.0000"
        assert rows[0]["duration_seconds"] == "1.50"

        # Check second row (failure)
        assert rows[1]["scenario_name"] == "scenario-2"
        assert rows[1]["status"] == "sbom_failed"
        assert rows[1]["precision"] == ""
        assert rows[1]["error_message"] == "Tool failed"

    def test_export_csv_empty(self, tmp_path):
        """Test exporting empty results."""
        output_path = tmp_path / "results.csv"

        export_benchmark_csv([], output_path)

        assert output_path.exists()

        with open(output_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 0

    def test_export_csv_headers(self, tmp_path):
        """Test that CSV has correct headers."""
        output_path = tmp_path / "results.csv"

        export_benchmark_csv([], output_path)

        with open(output_path) as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

        expected_headers = [
            "scenario_name",
            "package_manager",
            "tool_name",
            "status",
            "satisfiable",
            "true_positives",
            "false_positives",
            "false_negatives",
            "precision",
            "recall",
            "f1_score",
            "duration_seconds",
            "error_message",
        ]

        assert headers == expected_headers
