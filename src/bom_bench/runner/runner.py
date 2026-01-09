"""Sandbox-based benchmark runner.

Orchestrates running SCA tools against fixtures using sandboxes.
"""

from collections.abc import Callable
from pathlib import Path

from bom_bench.console import console
from bom_bench.fixtures.loader import FixtureSetLoader
from bom_bench.logging import get_logger
from bom_bench.models.sandbox import SandboxConfig
from bom_bench.models.sca_tool import BenchmarkResult, BenchmarkStatus, BenchmarkSummary
from bom_bench.renderers import render_results
from bom_bench.runner.executor import FixtureExecutor
from bom_bench.sca_tools import get_tool_config

logger = get_logger(__name__)


class BenchmarkRunner:
    """Orchestrates benchmarking using sandbox execution.

    The BenchmarkRunner:
    1. Loads fixture sets using FixtureSetLoader
    2. For each fixture + tool combination:
       - Creates a sandbox with fixture + tool environments
       - Runs SCA tool via mise
       - Compares actual vs expected SBOMs
    3. Aggregates and reports metrics
    """

    def __init__(
        self,
        output_dir: Path,
        sandbox_config: SandboxConfig | None = None,
    ):
        """Initialize benchmark runner.

        Args:
            output_dir: Directory for benchmark outputs
            sandbox_config: Configuration for sandbox execution
        """
        self.output_dir = output_dir
        self.sandbox_config = sandbox_config or SandboxConfig()
        self.loader = FixtureSetLoader()
        self.executor = FixtureExecutor(config=self.sandbox_config)

    def run(
        self,
        tools: list[str],
        fixture_sets: list[str] | None = None,
        fixtures: list[str] | None = None,
        progress_callback: Callable | None = None,
    ) -> list[BenchmarkSummary]:
        """Run benchmarks for specified tools and fixtures.

        Args:
            tools: List of SCA tool names to run
            fixture_sets: Optional list of fixture set names to use
            fixtures: Optional list of specific fixture names to run
            progress_callback: Optional callback called after each fixture execution
                             Signature: callback(tool_name, fixture_set_name, fixture_name, result)

        Returns:
            List of BenchmarkSummary objects for each tool/fixture set
        """
        summaries = []

        # Load fixture sets
        all_fixture_sets = self.loader.load_all()
        if fixture_sets:
            all_fixture_sets = [fs for fs in all_fixture_sets if fs.name in fixture_sets]

        if not all_fixture_sets:
            logger.warning("No fixture sets found")
            return []

        # Run benchmarks for each tool
        for tool_name in tools:
            tool_config = get_tool_config(tool_name)
            if tool_config is None:
                logger.warning(f"Tool '{tool_name}' not found or has no config")
                continue

            console.print()
            console.print(f"[bold]=== Tool: {tool_name} ===[/bold]")

            # Run for each fixture set
            for fixture_set in all_fixture_sets:
                logger.info(f"  Fixture Set: {fixture_set.name}")

                summary = BenchmarkSummary(
                    package_manager=fixture_set.name,
                    tool_name=tool_name,
                )

                # Filter fixtures if specified
                fixtures_to_run = fixture_set.fixtures
                if fixtures:
                    fixtures_to_run = [f for f in fixtures_to_run if f.name in fixtures]

                if not fixtures_to_run:
                    logger.warning(f"  No fixtures to run in {fixture_set.name}")
                    continue

                # Execute each fixture
                for fixture in fixtures_to_run:
                    result = self.executor.execute(
                        fixture=fixture,
                        fixture_set_env=fixture_set.environment,
                        tool_config=tool_config,
                        fixture_set_name=fixture_set.name,
                        output_dir=self.output_dir,
                    )
                    summary.add_result(result)
                    self._log_result(result)

                    if progress_callback:
                        progress_callback(tool_name, fixture_set.name, fixture.name, result)

                # Calculate aggregates
                summary.calculate_aggregates()
                summaries.append(summary)

                # Print summary
                summary.print_summary()

        # Render results to files
        render_results(summaries, self.output_dir)

        return summaries

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
