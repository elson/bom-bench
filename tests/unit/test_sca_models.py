"""Tests for SCA tool and benchmark models."""

import pytest
from pathlib import Path

from bom_bench.models.sca import (
    SBOMGenerationStatus,
    SCAToolInfo,
    SBOMResult,
    BenchmarkStatus,
    PurlMetrics,
    BenchmarkResult,
    BenchmarkSummary,
)


class TestSCAToolInfo:
    """Tests for SCAToolInfo model."""

    def test_create_tool_info(self):
        """Test creating SCAToolInfo."""
        info = SCAToolInfo(
            name="cdxgen",
            version="10.0.0",
            description="CycloneDX Generator",
            supported_ecosystems=["python", "javascript"],
            homepage="https://github.com/CycloneDX/cdxgen"
        )

        assert info.name == "cdxgen"
        assert info.version == "10.0.0"
        assert info.description == "CycloneDX Generator"
        assert "python" in info.supported_ecosystems
        assert info.homepage == "https://github.com/CycloneDX/cdxgen"

    def test_tool_info_defaults(self):
        """Test SCAToolInfo default values."""
        info = SCAToolInfo(name="test-tool")

        assert info.name == "test-tool"
        assert info.version is None
        assert info.description is None
        assert info.supported_ecosystems == []
        assert info.homepage is None
        assert info.installed is False

    def test_from_dict_full(self):
        """Test creating SCAToolInfo from dict with all fields."""
        data = {
            "name": "cdxgen",
            "version": "10.0.0",
            "description": "CycloneDX Generator",
            "supported_ecosystems": ["python", "javascript"],
            "homepage": "https://github.com/CycloneDX/cdxgen",
            "installed": True
        }

        info = SCAToolInfo.from_dict(data)

        assert info.name == "cdxgen"
        assert info.version == "10.0.0"
        assert info.description == "CycloneDX Generator"
        assert info.supported_ecosystems == ["python", "javascript"]
        assert info.homepage == "https://github.com/CycloneDX/cdxgen"
        assert info.installed is True

    def test_from_dict_minimal(self):
        """Test creating SCAToolInfo from dict with only required fields."""
        data = {"name": "test-tool"}

        info = SCAToolInfo.from_dict(data)

        assert info.name == "test-tool"
        assert info.version is None
        assert info.description is None
        assert info.supported_ecosystems == []
        assert info.homepage is None
        assert info.installed is False

    def test_from_dict_installed_false(self):
        """Test from_dict with installed explicitly set to False."""
        data = {"name": "test-tool", "installed": False}

        info = SCAToolInfo.from_dict(data)

        assert info.installed is False


class TestSBOMResult:
    """Tests for SBOMResult model."""

    def test_create_success_result(self):
        """Test creating successful SBOMResult."""
        result = SBOMResult.success(
            tool_name="cdxgen",
            sbom_path=Path("/output/sbom.json"),
            duration_seconds=1.5,
            exit_code=0
        )

        assert result.tool_name == "cdxgen"
        assert result.status == SBOMGenerationStatus.SUCCESS
        assert result.sbom_path == Path("/output/sbom.json")
        assert result.duration_seconds == 1.5
        assert result.exit_code == 0
        assert result.error_message is None

    def test_create_failed_result(self):
        """Test creating failed SBOMResult."""
        result = SBOMResult.failed(
            tool_name="cdxgen",
            error_message="Tool not found",
            status=SBOMGenerationStatus.TOOL_NOT_FOUND,
            duration_seconds=0.1
        )

        assert result.tool_name == "cdxgen"
        assert result.status == SBOMGenerationStatus.TOOL_NOT_FOUND
        assert result.error_message == "Tool not found"
        assert result.sbom_path is None

    def test_timeout_result(self):
        """Test creating timeout SBOMResult."""
        result = SBOMResult.failed(
            tool_name="cdxgen",
            error_message="Timeout after 120s",
            status=SBOMGenerationStatus.TIMEOUT,
            duration_seconds=120.0
        )

        assert result.status == SBOMGenerationStatus.TIMEOUT
        assert result.duration_seconds == 120.0

    def test_from_dict_success(self):
        """Test creating SBOMResult from success dict."""
        data = {
            "tool_name": "cdxgen",
            "status": "success",
            "sbom_path": "/output/sbom.json",
            "duration_seconds": 1.5,
            "exit_code": 0
        }

        result = SBOMResult.from_dict(data)

        assert result.tool_name == "cdxgen"
        assert result.status == SBOMGenerationStatus.SUCCESS
        assert result.sbom_path == Path("/output/sbom.json")
        assert result.duration_seconds == 1.5
        assert result.exit_code == 0
        assert result.error_message is None

    def test_from_dict_failed(self):
        """Test creating SBOMResult from failure dict."""
        data = {
            "tool_name": "cdxgen",
            "status": "tool_failed",
            "error_message": "Non-zero exit code",
            "duration_seconds": 0.5,
            "exit_code": 1
        }

        result = SBOMResult.from_dict(data)

        assert result.tool_name == "cdxgen"
        assert result.status == SBOMGenerationStatus.TOOL_FAILED
        assert result.error_message == "Non-zero exit code"
        assert result.sbom_path is None
        assert result.exit_code == 1

    def test_from_dict_timeout(self):
        """Test creating SBOMResult from timeout dict."""
        data = {
            "tool_name": "syft",
            "status": "timeout",
            "error_message": "Timeout after 120s",
            "duration_seconds": 120.0
        }

        result = SBOMResult.from_dict(data)

        assert result.status == SBOMGenerationStatus.TIMEOUT
        assert result.error_message == "Timeout after 120s"

    def test_from_dict_tool_not_found(self):
        """Test creating SBOMResult from tool_not_found dict."""
        data = {
            "tool_name": "cdxgen",
            "status": "tool_not_found",
            "error_message": "cdxgen not found in PATH"
        }

        result = SBOMResult.from_dict(data)

        assert result.status == SBOMGenerationStatus.TOOL_NOT_FOUND
        assert result.duration_seconds == 0.0

    def test_from_dict_parse_error(self):
        """Test creating SBOMResult from parse_error dict."""
        data = {
            "tool_name": "cdxgen",
            "status": "parse_error",
            "error_message": "Invalid JSON output",
            "duration_seconds": 1.0
        }

        result = SBOMResult.from_dict(data)

        assert result.status == SBOMGenerationStatus.PARSE_ERROR

    def test_from_dict_with_stdout_stderr(self):
        """Test creating SBOMResult with stdout/stderr."""
        data = {
            "tool_name": "cdxgen",
            "status": "tool_failed",
            "error_message": "Failed",
            "stdout": "Some output",
            "stderr": "Error details"
        }

        result = SBOMResult.from_dict(data)

        assert result.stdout == "Some output"
        assert result.stderr == "Error details"


class TestPurlMetrics:
    """Tests for PurlMetrics calculation."""

    def test_perfect_match(self):
        """Test metrics with perfect match."""
        expected = {"pkg:pypi/a@1.0", "pkg:pypi/b@2.0", "pkg:pypi/c@3.0"}
        actual = {"pkg:pypi/a@1.0", "pkg:pypi/b@2.0", "pkg:pypi/c@3.0"}

        metrics = PurlMetrics.calculate(expected, actual)

        assert metrics.true_positives == 3
        assert metrics.false_positives == 0
        assert metrics.false_negatives == 0
        assert metrics.precision == 1.0
        assert metrics.recall == 1.0
        assert metrics.f1_score == 1.0

    def test_partial_match(self):
        """Test metrics with partial match."""
        expected = {"pkg:pypi/a@1.0", "pkg:pypi/b@2.0", "pkg:pypi/c@3.0"}
        actual = {"pkg:pypi/a@1.0", "pkg:pypi/b@2.0", "pkg:pypi/d@4.0"}

        metrics = PurlMetrics.calculate(expected, actual)

        assert metrics.true_positives == 2
        assert metrics.false_positives == 1  # d is FP
        assert metrics.false_negatives == 1  # c is FN
        assert metrics.precision == pytest.approx(2/3)
        assert metrics.recall == pytest.approx(2/3)
        assert metrics.f1_score == pytest.approx(2/3)

    def test_no_match(self):
        """Test metrics with no match."""
        expected = {"pkg:pypi/a@1.0", "pkg:pypi/b@2.0"}
        actual = {"pkg:pypi/c@3.0", "pkg:pypi/d@4.0"}

        metrics = PurlMetrics.calculate(expected, actual)

        assert metrics.true_positives == 0
        assert metrics.false_positives == 2
        assert metrics.false_negatives == 2
        assert metrics.precision == 0.0
        assert metrics.recall == 0.0
        assert metrics.f1_score == 0.0

    def test_empty_expected(self):
        """Test metrics with empty expected set."""
        expected = set()
        actual = {"pkg:pypi/a@1.0"}

        metrics = PurlMetrics.calculate(expected, actual)

        assert metrics.true_positives == 0
        assert metrics.false_positives == 1
        assert metrics.false_negatives == 0
        assert metrics.precision == 0.0  # All false positives
        assert metrics.recall == 1.0  # Nothing to miss

    def test_empty_actual(self):
        """Test metrics with empty actual set."""
        expected = {"pkg:pypi/a@1.0"}
        actual = set()

        metrics = PurlMetrics.calculate(expected, actual)

        assert metrics.true_positives == 0
        assert metrics.false_positives == 0
        assert metrics.false_negatives == 1
        assert metrics.precision == 1.0  # No false positives
        assert metrics.recall == 0.0  # Missed everything

    def test_both_empty(self):
        """Test metrics with both sets empty - perfect score."""
        expected = set()
        actual = set()

        metrics = PurlMetrics.calculate(expected, actual)

        assert metrics.true_positives == 0
        assert metrics.false_positives == 0
        assert metrics.false_negatives == 0
        assert metrics.precision == 1.0  # No false positives
        assert metrics.recall == 1.0  # Nothing to miss
        assert metrics.f1_score == 1.0  # Perfect score


class TestBenchmarkResult:
    """Tests for BenchmarkResult model."""

    def test_create_successful_result(self):
        """Test creating successful BenchmarkResult."""
        metrics = PurlMetrics.calculate(
            {"pkg:pypi/a@1.0"},
            {"pkg:pypi/a@1.0"}
        )

        result = BenchmarkResult(
            scenario_name="test-scenario",
            package_manager="uv",
            tool_name="cdxgen",
            status=BenchmarkStatus.SUCCESS,
            metrics=metrics,
            expected_sbom_path=Path("/expected.json"),
            actual_sbom_path=Path("/actual.json")
        )

        assert result.scenario_name == "test-scenario"
        assert result.package_manager == "uv"
        assert result.tool_name == "cdxgen"
        assert result.status == BenchmarkStatus.SUCCESS
        assert result.metrics.precision == 1.0

    def test_unsatisfiable_result(self):
        """Test BenchmarkResult for unsatisfiable scenario."""
        result = BenchmarkResult(
            scenario_name="unsatisfiable-scenario",
            package_manager="uv",
            tool_name="cdxgen",
            status=BenchmarkStatus.UNSATISFIABLE,
            expected_satisfiable=False
        )

        assert result.status == BenchmarkStatus.UNSATISFIABLE
        assert result.expected_satisfiable is False
        assert result.metrics is None


class TestBenchmarkSummary:
    """Tests for BenchmarkSummary model."""

    def test_create_summary(self):
        """Test creating BenchmarkSummary."""
        summary = BenchmarkSummary(
            package_manager="uv",
            tool_name="cdxgen"
        )

        assert summary.package_manager == "uv"
        assert summary.tool_name == "cdxgen"
        assert summary.total_scenarios == 0
        assert summary.successful == 0
        assert summary.results == []

    def test_add_successful_result(self):
        """Test adding successful result to summary."""
        summary = BenchmarkSummary(package_manager="uv", tool_name="cdxgen")

        metrics = PurlMetrics.calculate({"a", "b"}, {"a", "b"})
        result = BenchmarkResult(
            scenario_name="test",
            package_manager="uv",
            tool_name="cdxgen",
            status=BenchmarkStatus.SUCCESS,
            metrics=metrics
        )

        summary.add_result(result)

        assert summary.total_scenarios == 1
        assert summary.successful == 1
        assert summary.total_true_positives == 2
        assert len(summary.results) == 1

    def test_add_failed_result(self):
        """Test adding failed result to summary."""
        summary = BenchmarkSummary(package_manager="uv", tool_name="cdxgen")

        result = BenchmarkResult(
            scenario_name="test",
            package_manager="uv",
            tool_name="cdxgen",
            status=BenchmarkStatus.SBOM_GENERATION_FAILED,
            error_message="Tool failed"
        )

        summary.add_result(result)

        assert summary.total_scenarios == 1
        assert summary.successful == 0
        assert summary.sbom_failed == 1

    def test_calculate_aggregates(self):
        """Test aggregate calculation."""
        summary = BenchmarkSummary(package_manager="uv", tool_name="cdxgen")

        # Add results with different metrics
        for precision, recall in [(0.8, 0.9), (0.9, 0.8), (1.0, 1.0)]:
            expected = {"a", "b", "c", "d", "e"}
            # Create actual set to get approximately these metrics
            if precision == 1.0:
                actual = expected
            else:
                actual = {"a", "b", "c", "f"}  # 3 TP, 1 FP, 2 FN

            metrics = PurlMetrics.calculate(expected, actual)
            result = BenchmarkResult(
                scenario_name=f"test-{precision}",
                package_manager="uv",
                tool_name="cdxgen",
                status=BenchmarkStatus.SUCCESS,
                metrics=metrics
            )
            summary.add_result(result)

        summary.calculate_aggregates()

        assert summary.successful == 3
        assert summary.mean_precision > 0
        assert summary.mean_recall > 0
        assert summary.mean_f1_score > 0
        assert summary.median_precision > 0

    def test_calculate_aggregates_empty(self):
        """Test aggregate calculation with no successful results."""
        summary = BenchmarkSummary(package_manager="uv", tool_name="cdxgen")

        # Add only failed results
        result = BenchmarkResult(
            scenario_name="test",
            package_manager="uv",
            tool_name="cdxgen",
            status=BenchmarkStatus.SBOM_GENERATION_FAILED
        )
        summary.add_result(result)

        # Should not raise
        summary.calculate_aggregates()

        assert summary.mean_precision == 0.0
        assert summary.mean_recall == 0.0
