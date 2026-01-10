"""Tests for model to_dict() serialization methods."""

from pathlib import Path

from bom_bench.models.sca_tool import (
    BenchmarkOverallSummary,
    BenchmarkResult,
    BenchmarkStatus,
    BenchmarkSummary,
    PurlMetrics,
)


class TestPurlMetricsToDict:
    """Tests for PurlMetrics.to_dict()."""

    def test_to_dict_with_all_fields(self):
        """Test serializing PurlMetrics with all fields populated."""
        expected_purls = {"pkg:pypi/foo@1.0.0", "pkg:pypi/bar@2.0.0"}
        actual_purls = {"pkg:pypi/foo@1.0.0", "pkg:pypi/baz@3.0.0"}

        metrics = PurlMetrics(
            true_positives=1,
            false_positives=1,
            false_negatives=1,
            precision=0.5,
            recall=0.5,
            f1_score=0.5,
            expected_purls=expected_purls,
            actual_purls=actual_purls,
        )

        result = metrics.to_dict()

        assert result == {
            "true_positives": 1,
            "false_positives": 1,
            "false_negatives": 1,
            "precision": 0.5,
            "recall": 0.5,
            "f1_score": 0.5,
            "expected_purls": ["pkg:pypi/bar@2.0.0", "pkg:pypi/foo@1.0.0"],
            "actual_purls": ["pkg:pypi/baz@3.0.0", "pkg:pypi/foo@1.0.0"],
        }

    def test_to_dict_with_empty_purls(self):
        """Test serializing PurlMetrics with empty PURL sets."""
        metrics = PurlMetrics(
            true_positives=0,
            false_positives=0,
            false_negatives=0,
            precision=1.0,
            recall=1.0,
            f1_score=0.0,
            expected_purls=set(),
            actual_purls=set(),
        )

        result = metrics.to_dict()

        assert result["expected_purls"] == []
        assert result["actual_purls"] == []


class TestBenchmarkResultToDict:
    """Tests for BenchmarkResult.to_dict()."""

    def test_to_dict_success_with_metrics(self):
        """Test serializing successful BenchmarkResult with metrics."""
        metrics = PurlMetrics(
            true_positives=5,
            false_positives=1,
            false_negatives=2,
            precision=0.833,
            recall=0.714,
            f1_score=0.769,
            expected_purls={"pkg:pypi/foo@1.0.0"},
            actual_purls={"pkg:pypi/foo@1.0.0"},
        )

        result = BenchmarkResult(
            scenario_name="test-scenario",
            package_manager="packse",
            tool_name="cdxgen",
            status=BenchmarkStatus.SUCCESS,
            metrics=metrics,
            expected_sbom_path=Path("/path/to/expected.cdx.json"),
            actual_sbom_path=Path("/path/to/actual.cdx.json"),
        )

        result_dict = result.to_dict()

        assert result_dict["scenario_name"] == "test-scenario"
        assert result_dict["tool_name"] == "cdxgen"
        assert result_dict["status"] == "success"
        assert result_dict["metrics"] is not None
        assert result_dict["metrics"]["true_positives"] == 5
        assert result_dict["expected_sbom_path"] == "/path/to/expected.cdx.json"
        assert result_dict["actual_sbom_path"] == "/path/to/actual.cdx.json"
        assert result_dict["error_message"] is None

    def test_to_dict_failed_without_metrics(self):
        """Test serializing failed BenchmarkResult without metrics."""
        result = BenchmarkResult(
            scenario_name="test-scenario",
            package_manager="packse",
            tool_name="cdxgen",
            status=BenchmarkStatus.SBOM_GENERATION_FAILED,
            metrics=None,
            error_message="Tool execution failed",
        )

        result_dict = result.to_dict()

        assert result_dict["status"] == "sbom_failed"
        assert result_dict["metrics"] is None
        assert result_dict["error_message"] == "Tool execution failed"
        assert result_dict["expected_sbom_path"] is None
        assert result_dict["actual_sbom_path"] is None

    def test_to_dict_unsatisfiable(self):
        """Test serializing unsatisfiable BenchmarkResult."""
        result = BenchmarkResult(
            scenario_name="test-unsatisfiable",
            package_manager="packse",
            tool_name="syft",
            status=BenchmarkStatus.UNSATISFIABLE,
            expected_satisfiable=False,
        )

        result_dict = result.to_dict()

        assert result_dict["status"] == "unsatisfiable"


class TestBenchmarkSummaryToDict:
    """Tests for BenchmarkSummary.to_dict()."""

    def test_to_dict_with_results(self):
        """Test serializing BenchmarkSummary with results."""
        metrics1 = PurlMetrics(
            true_positives=5,
            false_positives=1,
            false_negatives=2,
            precision=0.833,
            recall=0.714,
            f1_score=0.769,
        )
        result1 = BenchmarkResult(
            scenario_name="scenario-1",
            package_manager="packse",
            tool_name="cdxgen",
            status=BenchmarkStatus.SUCCESS,
            metrics=metrics1,
        )

        metrics2 = PurlMetrics(
            true_positives=3,
            false_positives=0,
            false_negatives=1,
            precision=1.0,
            recall=0.75,
            f1_score=0.857,
        )
        result2 = BenchmarkResult(
            scenario_name="scenario-2",
            package_manager="packse",
            tool_name="cdxgen",
            status=BenchmarkStatus.SUCCESS,
            metrics=metrics2,
        )

        summary = BenchmarkSummary(
            package_manager="packse",
            tool_name="cdxgen",
        )
        summary.add_result(result1)
        summary.add_result(result2)
        summary.calculate_aggregates()

        summary_dict = summary.to_dict()

        assert summary_dict["fixture_set"] == "packse"
        assert summary_dict["tool_name"] == "cdxgen"
        assert summary_dict["total_scenarios"] == 2
        assert summary_dict["successful"] == 2
        assert summary_dict["sbom_failed"] == 0
        assert summary_dict["total_true_positives"] == 8
        assert summary_dict["total_false_positives"] == 1
        assert summary_dict["total_false_negatives"] == 3
        assert len(summary_dict["results"]) == 2
        assert summary_dict["results"][0]["scenario_name"] == "scenario-1"
        assert summary_dict["results"][1]["scenario_name"] == "scenario-2"

    def test_to_dict_empty_summary(self):
        """Test serializing empty BenchmarkSummary."""
        summary = BenchmarkSummary(
            package_manager="packse",
            tool_name="syft",
        )

        summary_dict = summary.to_dict()

        assert summary_dict["total_scenarios"] == 0
        assert summary_dict["successful"] == 0
        assert summary_dict["results"] == []
        assert summary_dict["mean_precision"] == 0.0
        assert summary_dict["mean_recall"] == 0.0
        assert summary_dict["mean_f1_score"] == 0.0

    def test_to_dict_with_failures(self):
        """Test serializing BenchmarkSummary with mixed success and failures."""
        result1 = BenchmarkResult(
            scenario_name="success",
            package_manager="packse",
            tool_name="cdxgen",
            status=BenchmarkStatus.SUCCESS,
            metrics=PurlMetrics(true_positives=5, false_positives=0, false_negatives=0),
        )
        result2 = BenchmarkResult(
            scenario_name="failed",
            package_manager="packse",
            tool_name="cdxgen",
            status=BenchmarkStatus.SBOM_GENERATION_FAILED,
        )
        result3 = BenchmarkResult(
            scenario_name="unsatisfiable",
            package_manager="packse",
            tool_name="cdxgen",
            status=BenchmarkStatus.UNSATISFIABLE,
        )

        summary = BenchmarkSummary(
            package_manager="packse",
            tool_name="cdxgen",
        )
        summary.add_result(result1)
        summary.add_result(result2)
        summary.add_result(result3)

        summary_dict = summary.to_dict()

        assert summary_dict["total_scenarios"] == 3
        assert summary_dict["successful"] == 1
        assert summary_dict["sbom_failed"] == 1
        assert summary_dict["unsatisfiable"] == 1


class TestBenchmarkOverallSummaryFromSummaries:
    """Tests for BenchmarkOverallSummary.from_summaries()."""

    def test_from_summaries_with_successful_results(self):
        """Test aggregating multiple successful BenchmarkSummaries."""
        # Create first summary
        result1 = BenchmarkResult(
            scenario_name="scenario-1",
            package_manager="packse",
            tool_name="cdxgen",
            status=BenchmarkStatus.SUCCESS,
            metrics=PurlMetrics(
                true_positives=5,
                false_positives=1,
                false_negatives=2,
                precision=0.833,
                recall=0.714,
                f1_score=0.769,
            ),
        )
        summary1 = BenchmarkSummary(package_manager="packse", tool_name="cdxgen")
        summary1.add_result(result1)
        summary1.calculate_aggregates()

        # Create second summary
        result2 = BenchmarkResult(
            scenario_name="scenario-2",
            package_manager="npm",
            tool_name="cdxgen",
            status=BenchmarkStatus.SUCCESS,
            metrics=PurlMetrics(
                true_positives=3,
                false_positives=0,
                false_negatives=1,
                precision=1.0,
                recall=0.75,
                f1_score=0.857,
            ),
        )
        summary2 = BenchmarkSummary(package_manager="npm", tool_name="cdxgen")
        summary2.add_result(result2)
        summary2.calculate_aggregates()

        # Aggregate
        overall = BenchmarkOverallSummary.from_summaries("cdxgen", [summary1, summary2])

        assert overall.tool_name == "cdxgen"
        assert overall.fixture_sets == 2
        assert overall.total_scenarios == 2
        assert overall.successful == 2
        assert overall.mean_precision == (0.833 + 1.0) / 2
        assert overall.mean_recall == (0.714 + 0.75) / 2
        assert overall.mean_f1_score == (0.769 + 0.857) / 2
        assert overall.median_precision == (0.833 + 1.0) / 2  # median of 2 values is mean
        assert overall.median_recall == (0.714 + 0.75) / 2
        assert overall.median_f1_score == (0.769 + 0.857) / 2

    def test_from_summaries_with_no_successful_results(self):
        """Test aggregating summaries with no successful results."""
        result1 = BenchmarkResult(
            scenario_name="failed-1",
            package_manager="packse",
            tool_name="syft",
            status=BenchmarkStatus.SBOM_GENERATION_FAILED,
            error_message="Tool failed",
        )
        summary1 = BenchmarkSummary(package_manager="packse", tool_name="syft")
        summary1.add_result(result1)
        summary1.calculate_aggregates()

        result2 = BenchmarkResult(
            scenario_name="unsatisfiable-1",
            package_manager="npm",
            tool_name="syft",
            status=BenchmarkStatus.UNSATISFIABLE,
        )
        summary2 = BenchmarkSummary(package_manager="npm", tool_name="syft")
        summary2.add_result(result2)
        summary2.calculate_aggregates()

        overall = BenchmarkOverallSummary.from_summaries("syft", [summary1, summary2])

        assert overall.tool_name == "syft"
        assert overall.fixture_sets == 2
        assert overall.total_scenarios == 2
        assert overall.successful == 0
        assert overall.mean_precision == 0.0
        assert overall.mean_recall == 0.0
        assert overall.mean_f1_score == 0.0
        assert overall.median_precision == 0.0
        assert overall.median_recall == 0.0
        assert overall.median_f1_score == 0.0

    def test_from_summaries_with_mixed_results(self):
        """Test aggregating summaries with mix of successful and failed results."""
        # Successful summary
        result1 = BenchmarkResult(
            scenario_name="success-1",
            package_manager="packse",
            tool_name="cdxgen",
            status=BenchmarkStatus.SUCCESS,
            metrics=PurlMetrics(
                true_positives=10,
                false_positives=0,
                false_negatives=0,
                precision=1.0,
                recall=1.0,
                f1_score=1.0,
            ),
        )
        summary1 = BenchmarkSummary(package_manager="packse", tool_name="cdxgen")
        summary1.add_result(result1)
        summary1.calculate_aggregates()

        # Failed summary
        result2 = BenchmarkResult(
            scenario_name="failed-1",
            package_manager="npm",
            tool_name="cdxgen",
            status=BenchmarkStatus.SBOM_GENERATION_FAILED,
        )
        summary2 = BenchmarkSummary(package_manager="npm", tool_name="cdxgen")
        summary2.add_result(result2)
        summary2.calculate_aggregates()

        overall = BenchmarkOverallSummary.from_summaries("cdxgen", [summary1, summary2])

        assert overall.fixture_sets == 2
        assert overall.total_scenarios == 2
        assert overall.successful == 1
        # Only successful summary's metrics are included in aggregation
        assert overall.mean_precision == 1.0
        assert overall.mean_recall == 1.0
        assert overall.mean_f1_score == 1.0

    def test_from_summaries_empty_list(self):
        """Test aggregating empty list of summaries."""
        overall = BenchmarkOverallSummary.from_summaries("test-tool", [])

        assert overall.tool_name == "test-tool"
        assert overall.fixture_sets == 0
        assert overall.total_scenarios == 0
        assert overall.successful == 0
        assert overall.mean_precision == 0.0
        assert overall.mean_recall == 0.0
        assert overall.mean_f1_score == 0.0


class TestBenchmarkOverallSummaryToDict:
    """Tests for BenchmarkOverallSummary.to_dict()."""

    def test_to_dict_with_all_fields(self):
        """Test serializing BenchmarkOverallSummary with all fields."""
        overall = BenchmarkOverallSummary(
            tool_name="cdxgen",
            fixture_sets=3,
            total_scenarios=42,
            successful=38,
            mean_precision=0.9523,
            mean_recall=0.8765,
            mean_f1_score=0.9123,
            median_precision=0.9600,
            median_recall=0.8800,
            median_f1_score=0.9200,
        )

        result = overall.to_dict()

        assert result == {
            "tool_name": "cdxgen",
            "fixture_sets": 3,
            "total_scenarios": 42,
            "successful": 38,
            "mean_precision": 0.9523,
            "mean_recall": 0.8765,
            "mean_f1_score": 0.9123,
            "median_precision": 0.9600,
            "median_recall": 0.8800,
            "median_f1_score": 0.9200,
        }

    def test_to_dict_with_zero_metrics(self):
        """Test serializing BenchmarkOverallSummary with zero metrics."""
        overall = BenchmarkOverallSummary(
            tool_name="syft",
            fixture_sets=2,
            total_scenarios=10,
            successful=0,
        )

        result = overall.to_dict()

        assert result["tool_name"] == "syft"
        assert result["mean_precision"] == 0.0
        assert result["mean_recall"] == 0.0
        assert result["mean_f1_score"] == 0.0
        assert result["median_precision"] == 0.0
        assert result["median_recall"] == 0.0
        assert result["median_f1_score"] == 0.0
