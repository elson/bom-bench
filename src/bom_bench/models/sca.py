"""SCA tool and benchmark result models."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set
import statistics

import click

from bom_bench.logging_config import get_logger

logger = get_logger(__name__)


class SBOMGenerationStatus(Enum):
    """Status of SBOM generation by an SCA tool."""

    SUCCESS = "success"
    """Tool ran successfully, SBOM generated"""

    TOOL_FAILED = "tool_failed"
    """Tool execution failed (non-zero exit)"""

    TIMEOUT = "timeout"
    """Tool timed out"""

    PARSE_ERROR = "parse_error"
    """Output could not be parsed as valid SBOM"""

    TOOL_NOT_FOUND = "tool_not_found"
    """Tool not installed"""


@dataclass
class SCAToolInfo:
    """Metadata about an SCA tool provided by a plugin.

    Plugins return this from bom_bench_register_sca_tools() to
    describe what tools they provide.
    """

    name: str
    """Tool identifier (e.g., 'cdxgen', 'syft')"""

    version: Optional[str] = None
    """Tool version string"""

    description: Optional[str] = None
    """Human-readable description"""

    supported_ecosystems: List[str] = field(default_factory=list)
    """Ecosystems this tool supports (e.g., ['python', 'javascript'])"""

    homepage: Optional[str] = None
    """Tool homepage URL"""


@dataclass
class SBOMResult:
    """Result of SBOM generation from a plugin.

    Plugins return this from bom_bench_generate_sbom() to report
    what happened when they invoked their tool.
    """

    tool_name: str
    """Name of the tool that generated this result"""

    status: SBOMGenerationStatus
    """Generation status"""

    sbom_path: Optional[Path] = None
    """Path to generated SBOM file (if successful)"""

    duration_seconds: float = 0.0
    """Time taken to generate SBOM"""

    exit_code: Optional[int] = None
    """Tool exit code (if subprocess)"""

    error_message: Optional[str] = None
    """Error message if generation failed"""

    stdout: Optional[str] = None
    """Tool stdout (for debugging)"""

    stderr: Optional[str] = None
    """Tool stderr (for debugging)"""

    @classmethod
    def success(
        cls,
        tool_name: str,
        sbom_path: Path,
        duration_seconds: float,
        exit_code: int = 0
    ) -> "SBOMResult":
        """Create a successful result."""
        return cls(
            tool_name=tool_name,
            status=SBOMGenerationStatus.SUCCESS,
            sbom_path=sbom_path,
            duration_seconds=duration_seconds,
            exit_code=exit_code
        )

    @classmethod
    def failed(
        cls,
        tool_name: str,
        error_message: str,
        status: SBOMGenerationStatus = SBOMGenerationStatus.TOOL_FAILED,
        duration_seconds: float = 0.0,
        exit_code: Optional[int] = None
    ) -> "SBOMResult":
        """Create a failed result."""
        return cls(
            tool_name=tool_name,
            status=status,
            error_message=error_message,
            duration_seconds=duration_seconds,
            exit_code=exit_code
        )


class BenchmarkStatus(Enum):
    """Status of a benchmark comparison."""

    SUCCESS = "success"
    """Comparison completed successfully"""

    SBOM_GENERATION_FAILED = "sbom_failed"
    """Tool failed to generate SBOM"""

    UNSATISFIABLE = "unsatisfiable"
    """Expected marked as unsatisfiable"""

    PARSE_ERROR = "parse_error"
    """SBOM parsing failed"""

    MISSING_EXPECTED = "missing_expected"
    """expected.cdx.json not found"""


@dataclass
class PurlMetrics:
    """Metrics from PURL comparison."""

    true_positives: int = 0
    """Number of PURLs in both expected and actual"""

    false_positives: int = 0
    """Number of PURLs in actual but not expected"""

    false_negatives: int = 0
    """Number of PURLs in expected but not actual"""

    precision: float = 0.0
    """TP / (TP + FP) - fraction of detected packages that are correct"""

    recall: float = 0.0
    """TP / (TP + FN) - fraction of expected packages detected"""

    f1_score: float = 0.0
    """Harmonic mean of precision and recall"""

    expected_purls: Set[str] = field(default_factory=set)
    """Set of expected PURLs"""

    actual_purls: Set[str] = field(default_factory=set)
    """Set of actual PURLs"""

    @classmethod
    def calculate(cls, expected_purls: Set[str], actual_purls: Set[str]) -> "PurlMetrics":
        """Calculate metrics from two sets of purls.

        Args:
            expected_purls: Set of expected package URLs
            actual_purls: Set of actual package URLs from SCA tool

        Returns:
            PurlMetrics with calculated precision, recall, and F1
        """
        tp = len(expected_purls & actual_purls)
        fp = len(actual_purls - expected_purls)
        fn = len(expected_purls - actual_purls)

        # When denominator is 0, use 1.0 (no errors possible)
        # - precision: if nothing detected, no false positives → 1.0
        # - recall: if nothing expected, nothing to miss → 1.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1_score = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        return cls(
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            expected_purls=expected_purls,
            actual_purls=actual_purls,
        )


@dataclass
class BenchmarkResult:
    """Result of benchmarking a single scenario."""

    scenario_name: str
    """Name of the scenario that was benchmarked"""

    package_manager: str
    """Package manager used (e.g., 'uv', 'pip')"""

    tool_name: str
    """SCA tool used for benchmarking"""

    status: BenchmarkStatus
    """Benchmark execution status"""

    metrics: Optional[PurlMetrics] = None
    """Comparison metrics (None if benchmark failed)"""

    expected_satisfiable: bool = True
    """Whether the expected SBOM was satisfiable"""

    sbom_result: Optional[SBOMResult] = None
    """Result from SBOM generation"""

    expected_sbom_path: Optional[Path] = None
    """Path to expected SBOM file"""

    actual_sbom_path: Optional[Path] = None
    """Path to actual SBOM file from SCA tool"""

    error_message: Optional[str] = None
    """Error message if benchmark failed"""


@dataclass
class BenchmarkSummary:
    """Aggregated benchmark metrics across multiple scenarios."""

    package_manager: str
    """Package manager being benchmarked"""

    tool_name: str
    """SCA tool used for benchmarking"""

    total_scenarios: int = 0
    """Total number of scenarios processed"""

    successful: int = 0
    """Number of successful benchmarks"""

    sbom_failed: int = 0
    """Number of SBOM generation failures"""

    unsatisfiable: int = 0
    """Number of unsatisfiable scenarios"""

    parse_errors: int = 0
    """Number of parse errors"""

    missing_expected: int = 0
    """Number of missing expected SBOMs"""

    mean_precision: float = 0.0
    """Mean precision across successful runs"""

    mean_recall: float = 0.0
    """Mean recall across successful runs"""

    mean_f1_score: float = 0.0
    """Mean F1 score across successful runs"""

    median_precision: float = 0.0
    """Median precision across successful runs"""

    median_recall: float = 0.0
    """Median recall across successful runs"""

    median_f1_score: float = 0.0
    """Median F1 score across successful runs"""

    total_true_positives: int = 0
    """Sum of all true positives"""

    total_false_positives: int = 0
    """Sum of all false positives"""

    total_false_negatives: int = 0
    """Sum of all false negatives"""

    results: List[BenchmarkResult] = field(default_factory=list)
    """Individual benchmark results"""

    def add_result(self, result: BenchmarkResult) -> None:
        """Add a benchmark result and update counts.

        Args:
            result: Benchmark result to add
        """
        self.results.append(result)
        self.total_scenarios += 1

        if result.status == BenchmarkStatus.SUCCESS:
            self.successful += 1
            if result.metrics:
                self.total_true_positives += result.metrics.true_positives
                self.total_false_positives += result.metrics.false_positives
                self.total_false_negatives += result.metrics.false_negatives
        elif result.status == BenchmarkStatus.SBOM_GENERATION_FAILED:
            self.sbom_failed += 1
        elif result.status == BenchmarkStatus.UNSATISFIABLE:
            self.unsatisfiable += 1
        elif result.status == BenchmarkStatus.PARSE_ERROR:
            self.parse_errors += 1
        elif result.status == BenchmarkStatus.MISSING_EXPECTED:
            self.missing_expected += 1

    def calculate_aggregates(self) -> None:
        """Calculate mean and median metrics from successful runs."""
        successful_results = [
            r for r in self.results
            if r.status == BenchmarkStatus.SUCCESS and r.metrics
        ]

        if not successful_results:
            return

        precisions = [r.metrics.precision for r in successful_results]
        recalls = [r.metrics.recall for r in successful_results]
        f1_scores = [r.metrics.f1_score for r in successful_results]

        self.mean_precision = statistics.mean(precisions)
        self.mean_recall = statistics.mean(recalls)
        self.mean_f1_score = statistics.mean(f1_scores)

        self.median_precision = statistics.median(precisions)
        self.median_recall = statistics.median(recalls)
        self.median_f1_score = statistics.median(f1_scores)

    def print_summary(self) -> None:
        """Print a formatted summary with colored output."""
        logger.info("")
        logger.info(click.style(
            f"Benchmark Summary ({self.tool_name} / {self.package_manager}):",
            bold=True
        ))
        logger.info(f"  Total Scenarios: {self.total_scenarios}")
        logger.info("")

        logger.info(click.style("Status Breakdown:", bold=True))
        logger.info(
            f"  Successful: {click.style(str(self.successful), fg='green')}"
        )
        if self.sbom_failed > 0:
            logger.warning(
                f"  SBOM Failed: {click.style(str(self.sbom_failed), fg='red')}"
            )
        if self.unsatisfiable > 0:
            logger.info(f"  Unsatisfiable: {self.unsatisfiable}")
        if self.parse_errors > 0:
            logger.warning(
                f"  Parse Errors: {click.style(str(self.parse_errors), fg='red')}"
            )
        if self.missing_expected > 0:
            logger.warning(
                f"  Missing Expected: {click.style(str(self.missing_expected), fg='red')}"
            )

        if self.successful > 0:
            logger.info("")
            logger.info(click.style("Metrics (across successful runs):", bold=True))
            logger.info(f"  Mean Precision: {self.mean_precision:.3f}")
            logger.info(f"  Mean Recall: {self.mean_recall:.3f}")
            logger.info(f"  Mean F1 Score: {self.mean_f1_score:.3f}")
            logger.info("")
            logger.info(f"  Median Precision: {self.median_precision:.3f}")
            logger.info(f"  Median Recall: {self.median_recall:.3f}")
            logger.info(f"  Median F1 Score: {self.median_f1_score:.3f}")
            logger.info("")
            logger.info(f"  Total TP: {self.total_true_positives}")
            logger.info(f"  Total FP: {self.total_false_positives}")
            logger.info(f"  Total FN: {self.total_false_negatives}")
