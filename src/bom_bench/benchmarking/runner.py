"""Benchmark runner orchestrating SCA tools via plugins.

This module coordinates running SCA tools against generated projects,
comparing their output with expected SBOMs, and collecting metrics.
"""

from pathlib import Path
from typing import List, Optional

import click

from bom_bench.logging_config import get_logger
from bom_bench.models.sca import (
    BenchmarkResult,
    BenchmarkStatus,
    BenchmarkSummary,
    PurlMetrics,
    SBOMGenerationStatus,
)
from bom_bench.sca_tools import generate_sbom, get_registered_tools
from bom_bench.benchmarking.comparison import (
    extract_purls_from_cyclonedx,
    load_expected_sbom,
    load_actual_sbom,
)
from bom_bench.benchmarking.storage import (
    save_benchmark_result,
    save_benchmark_summary,
    export_benchmark_csv,
)
from bom_bench.package_managers import list_available_package_managers

logger = get_logger(__name__)


# Ecosystem mapping for package managers
PM_ECOSYSTEMS = {
    "uv": "python",
    "pip": "python",
    "pnpm": "javascript",
    "npm": "javascript",
    "gradle": "java",
    "maven": "java",
}


class BenchmarkRunner:
    """Orchestrates benchmarking across SCA tools and package managers.

    The BenchmarkRunner:
    1. Discovers scenario directories from previous setup runs
    2. Runs SCA tools via plugins to generate actual SBOMs
    3. Compares actual vs expected SBOMs using PURL comparison
    4. Calculates and reports metrics (precision, recall, F1)
    5. Saves results in JSON and CSV formats
    """

    def __init__(
        self,
        output_dir: Path,
        benchmarks_dir: Path,
        tools: List[str]
    ):
        """Initialize benchmark runner.

        Args:
            output_dir: Directory containing generated projects from setup
            benchmarks_dir: Directory for benchmark outputs
            tools: List of SCA tool names to run
        """
        self.output_dir = output_dir
        self.benchmarks_dir = benchmarks_dir
        self.tools = tools

    def run(
        self,
        package_managers: str,
        scenarios: Optional[List[str]] = None
    ) -> int:
        """Run benchmarks for all tools and package managers.

        Args:
            package_managers: Comma-separated PM names or 'all'
            scenarios: Optional list of specific scenario names to benchmark

        Returns:
            Exit code (0 for success)
        """
        # Parse package managers
        if package_managers.lower() == "all":
            pm_list = list_available_package_managers()
        else:
            pm_list = [pm.strip() for pm in package_managers.split(",")]

        has_errors = False

        # Run benchmarks for each tool
        for tool_name in self.tools:
            tool_info = get_registered_tools().get(tool_name)
            logger.info("")
            logger.info(click.style(f"=== Tool: {tool_name} ===", bold=True))

            for pm_name in pm_list:
                logger.info(f"  Package Manager: {pm_name}")

                # Find scenario directories (under scenarios/{pm_name}/)
                pm_dir = self.output_dir / "scenarios" / pm_name
                if not pm_dir.exists():
                    logger.warning(f"  No output found for {pm_name}")
                    continue

                scenario_dirs = sorted([d for d in pm_dir.iterdir() if d.is_dir()])

                # Filter by scenario names if provided
                if scenarios:
                    scenario_dirs = [d for d in scenario_dirs if d.name in scenarios]

                if not scenario_dirs:
                    logger.warning(f"  No scenarios found for {pm_name}")
                    continue

                # Create summary for this tool/PM combination
                summary = BenchmarkSummary(
                    package_manager=pm_name,
                    tool_name=tool_name
                )

                # Benchmark each scenario
                for scenario_dir in scenario_dirs:
                    result = self._benchmark_scenario(
                        tool_name=tool_name,
                        pm_name=pm_name,
                        scenario_name=scenario_dir.name,
                        scenario_dir=scenario_dir,
                        ecosystem=PM_ECOSYSTEMS.get(pm_name, "unknown")
                    )
                    summary.add_result(result)

                    # Log progress
                    self._log_result(result)

                # Calculate aggregates
                summary.calculate_aggregates()

                # Save results
                self._save_results(summary, tool_name, pm_name)

                # Print summary
                summary.print_summary()

                if summary.sbom_failed > 0 or summary.parse_errors > 0:
                    has_errors = True

        return 1 if has_errors else 0

    def _benchmark_scenario(
        self,
        tool_name: str,
        pm_name: str,
        scenario_name: str,
        scenario_dir: Path,
        ecosystem: str
    ) -> BenchmarkResult:
        """Benchmark a single scenario.

        Args:
            tool_name: SCA tool to use
            pm_name: Package manager name
            scenario_name: Scenario name
            scenario_dir: Scenario directory (contains assets/ and expected.cdx.json)
            ecosystem: Package ecosystem (python, javascript, etc.)

        Returns:
            BenchmarkResult with comparison metrics
        """
        expected_path = scenario_dir / "expected.cdx.json"
        meta_path = scenario_dir / "meta.json"
        assets_dir = scenario_dir / "assets"
        actual_dir = self.benchmarks_dir / tool_name / pm_name / scenario_name
        actual_path = actual_dir / "actual.cdx.json"

        # Check if meta.json exists (new format) or expected SBOM exists (legacy)
        if not meta_path.exists() and not expected_path.exists():
            return BenchmarkResult(
                scenario_name=scenario_name,
                package_manager=pm_name,
                tool_name=tool_name,
                status=BenchmarkStatus.MISSING_EXPECTED,
                error_message="meta.json and expected.cdx.json not found"
            )

        # Load expected SBOM and check satisfiability
        # Pass meta_path if it exists (new format), otherwise use legacy format
        expected_sbom, satisfiable = load_expected_sbom(
            expected_path,
            meta_path=meta_path if meta_path.exists() else None
        )

        if not satisfiable:
            # Unsatisfiable scenario - still record but don't compare
            return BenchmarkResult(
                scenario_name=scenario_name,
                package_manager=pm_name,
                tool_name=tool_name,
                status=BenchmarkStatus.UNSATISFIABLE,
                expected_satisfiable=False,
                expected_sbom_path=expected_path
            )

        # Generate SBOM using plugin (scan the assets directory with project files)
        sbom_result = generate_sbom(
            tool_name=tool_name,
            project_dir=assets_dir,
            output_path=actual_path,
            ecosystem=ecosystem
        )

        if sbom_result is None:
            return BenchmarkResult(
                scenario_name=scenario_name,
                package_manager=pm_name,
                tool_name=tool_name,
                status=BenchmarkStatus.SBOM_GENERATION_FAILED,
                error_message=f"No plugin handled tool '{tool_name}'"
            )

        if sbom_result.status != SBOMGenerationStatus.SUCCESS:
            return BenchmarkResult(
                scenario_name=scenario_name,
                package_manager=pm_name,
                tool_name=tool_name,
                status=BenchmarkStatus.SBOM_GENERATION_FAILED,
                sbom_result=sbom_result,
                error_message=sbom_result.error_message
            )

        # Load actual SBOM
        actual_sbom = load_actual_sbom(actual_path)

        if actual_sbom is None:
            return BenchmarkResult(
                scenario_name=scenario_name,
                package_manager=pm_name,
                tool_name=tool_name,
                status=BenchmarkStatus.PARSE_ERROR,
                sbom_result=sbom_result,
                actual_sbom_path=actual_path,
                error_message="Failed to parse actual SBOM"
            )

        # Extract and compare PURLs
        expected_purls = extract_purls_from_cyclonedx(expected_sbom) if expected_sbom else set()
        actual_purls = extract_purls_from_cyclonedx(actual_sbom)

        metrics = PurlMetrics.calculate(expected_purls, actual_purls)

        return BenchmarkResult(
            scenario_name=scenario_name,
            package_manager=pm_name,
            tool_name=tool_name,
            status=BenchmarkStatus.SUCCESS,
            metrics=metrics,
            sbom_result=sbom_result,
            expected_sbom_path=expected_path,
            actual_sbom_path=actual_path
        )

    def _log_result(self, result: BenchmarkResult) -> None:
        """Log a single benchmark result."""
        if result.status == BenchmarkStatus.SUCCESS and result.metrics:
            logger.info(
                f"    {result.scenario_name}: "
                f"P={result.metrics.precision:.3f} "
                f"R={result.metrics.recall:.3f} "
                f"F1={result.metrics.f1_score:.3f}"
            )
        elif result.status == BenchmarkStatus.UNSATISFIABLE:
            logger.info(f"    {result.scenario_name}: unsatisfiable (skipped)")
        elif result.status == BenchmarkStatus.SBOM_GENERATION_FAILED:
            logger.warning(f"    {result.scenario_name}: SBOM generation failed")
        elif result.status == BenchmarkStatus.MISSING_EXPECTED:
            logger.warning(f"    {result.scenario_name}: missing expected SBOM")
        else:
            logger.info(f"    {result.scenario_name}: {result.status.value}")

    def _save_results(
        self,
        summary: BenchmarkSummary,
        tool_name: str,
        pm_name: str
    ) -> None:
        """Save benchmark results to files."""
        base_dir = self.benchmarks_dir / tool_name / pm_name
        base_dir.mkdir(parents=True, exist_ok=True)

        # Save individual results
        for result in summary.results:
            result_dir = base_dir / result.scenario_name
            result_dir.mkdir(parents=True, exist_ok=True)
            save_benchmark_result(result, result_dir / "result.json")

        # Save summary
        save_benchmark_summary(summary, base_dir / "summary.json")

        # Export CSV
        export_benchmark_csv(summary.results, base_dir / "results.csv")

        logger.info(f"  Results saved to {base_dir}")
