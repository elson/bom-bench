"""SCA tool and benchmark result models."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import click

from bom_bench.logging import get_logger

if TYPE_CHECKING:
    from bom_bench.sandbox.mise import ToolSpec

logger = get_logger(__name__)


@dataclass
class SCAToolInfo:
    """Metadata about an SCA tool provided by a plugin.

    Plugins return a dict from register_sca_tools() which is
    converted to this class via from_dict().
    """

    name: str
    """Tool identifier (e.g., 'cdxgen', 'syft')"""

    description: str | None = None
    """Human-readable description"""

    supported_ecosystems: list[str] = field(default_factory=list)
    """Ecosystems this tool supports (e.g., ['python', 'javascript'])"""

    homepage: str | None = None
    """Tool homepage URL"""

    tools: list[dict] = field(default_factory=list)
    """Mise tool specifications needed by this SCA tool"""

    @classmethod
    def from_dict(cls, d: dict) -> SCAToolInfo:
        """Create SCAToolInfo from plugin dict.

        Args:
            d: Dict with tool info fields

        Returns:
            SCAToolInfo instance
        """
        return cls(
            name=d["name"],
            description=d.get("description"),
            supported_ecosystems=d.get("supported_ecosystems", []),
            homepage=d.get("homepage"),
            tools=d.get("tools", []),
        )


@dataclass
class SCAToolConfig:
    """Declarative configuration for an SCA tool.

    Describes what the tool needs (mise tools) and how to invoke it (command).
    Actual execution happens in the Sandbox.
    """

    name: str
    """Tool identifier (e.g., 'cdxgen', 'syft')"""

    tools: list[ToolSpec]
    """Mise tool specifications needed by this SCA tool"""

    command: str
    """Command template with {output_path} and {project_dir} placeholders"""

    env_vars: dict[str, str] = field(default_factory=dict)
    """Environment variables to set when running the tool"""

    supported_ecosystems: list[str] = field(default_factory=list)
    """Ecosystems this tool supports (e.g., ['python', 'javascript'])"""

    description: str | None = None
    """Human-readable description"""

    @classmethod
    def from_dict(cls, data: dict) -> SCAToolConfig:
        """Create an SCAToolConfig from a dictionary."""
        from bom_bench.sandbox.mise import ToolSpec

        tools = [ToolSpec(name=t["name"], version=t["version"]) for t in data.get("tools", [])]
        return cls(
            name=data["name"],
            tools=tools,
            command=data["command"],
            env_vars=data.get("env_vars", {}),
            supported_ecosystems=data.get("supported_ecosystems", []),
            description=data.get("description"),
        )

    def format_command(self, output_path: str, project_dir: str) -> str:
        """Format the command template with actual paths.

        Args:
            output_path: Path where SBOM will be written
            project_dir: Path to the project directory

        Returns:
            Formatted command string ready for execution
        """
        return self.command.format(output_path=output_path, project_dir=project_dir)


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

    expected_purls: set[str] = field(default_factory=set)
    """Set of expected PURLs"""

    actual_purls: set[str] = field(default_factory=set)
    """Set of actual PURLs"""

    @classmethod
    def calculate(cls, expected_purls: set[str], actual_purls: set[str]) -> PurlMetrics:
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
            2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
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

    metrics: PurlMetrics | None = None
    """Comparison metrics (None if benchmark failed)"""

    expected_satisfiable: bool = True
    """Whether the expected SBOM was satisfiable"""

    expected_sbom_path: Path | None = None
    """Path to expected SBOM file"""

    actual_sbom_path: Path | None = None
    """Path to actual SBOM file from SCA tool"""

    error_message: str | None = None
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

    results: list[BenchmarkResult] = field(default_factory=list)
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
        successful_metrics = [
            r.metrics
            for r in self.results
            if r.status == BenchmarkStatus.SUCCESS and r.metrics is not None
        ]

        if not successful_metrics:
            return

        precisions = [m.precision for m in successful_metrics]
        recalls = [m.recall for m in successful_metrics]
        f1_scores = [m.f1_score for m in successful_metrics]

        self.mean_precision = statistics.mean(precisions)
        self.mean_recall = statistics.mean(recalls)
        self.mean_f1_score = statistics.mean(f1_scores)

        self.median_precision = statistics.median(precisions)
        self.median_recall = statistics.median(recalls)
        self.median_f1_score = statistics.median(f1_scores)

    def print_summary(self) -> None:
        """Print a formatted summary with colored output."""
        logger.info("")
        logger.info(
            click.style(
                f"Benchmark Summary ({self.tool_name} / {self.package_manager}):", bold=True
            )
        )
        logger.info(f"  Total Scenarios: {self.total_scenarios}")
        logger.info("")

        logger.info(click.style("Status Breakdown:", bold=True))
        logger.info(f"  Successful: {click.style(str(self.successful), fg='green')}")
        if self.sbom_failed > 0:
            logger.warning(f"  SBOM Failed: {click.style(str(self.sbom_failed), fg='red')}")
        if self.unsatisfiable > 0:
            logger.info(f"  Unsatisfiable: {self.unsatisfiable}")
        if self.parse_errors > 0:
            logger.warning(f"  Parse Errors: {click.style(str(self.parse_errors), fg='red')}")
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
