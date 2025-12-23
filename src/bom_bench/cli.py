"""Command-line interface for bom-bench."""

import sys
from pathlib import Path
from typing import List, Optional

import click

from bom_bench.config import (
    DEFAULT_PACKAGE_MANAGER,
    OUTPUT_DIR,
    UNIVERSAL_SCENARIOS_ONLY,
    EXCLUDE_NAME_PATTERNS,
)
from bom_bench.data.loader import ScenarioLoader
from bom_bench.logging_config import get_logger, setup_logging
from bom_bench.models.scenario import ScenarioFilter, Scenario
from bom_bench.models.result import ProcessingResult, ProcessingStatus, Summary
from bom_bench.package_managers import get_package_manager, list_available_package_managers

logger = get_logger(__name__)


class BomBenchCLI:
    """Command-line interface orchestrator for bom-bench."""

    def __init__(self):
        """Initialize CLI orchestrator."""
        self.scenario_loader = ScenarioLoader(auto_fetch=True)

    def parse_package_managers(self, pm_arg: str) -> List[str]:
        """Parse package manager argument.

        Args:
            pm_arg: Package manager argument string (e.g., 'uv,pip' or 'all')

        Returns:
            List of package manager names

        Raises:
            ValueError: If package manager is not available
        """
        if pm_arg.lower() == "all":
            return list_available_package_managers()

        pms = [pm.strip() for pm in pm_arg.split(",")]
        available = list_available_package_managers()

        for pm in pms:
            if pm not in available:
                raise ValueError(
                    f"Unknown package manager: {pm}. "
                    f"Available: {', '.join(available)}"
                )

        return pms

    def create_filter(
        self,
        universal_only: bool = UNIVERSAL_SCENARIOS_ONLY,
        scenario_names: Optional[List[str]] = None
    ) -> ScenarioFilter:
        """Create scenario filter configuration.

        Args:
            universal_only: Only include scenarios with universal=true
            scenario_names: Optional specific scenario names to include

        Returns:
            ScenarioFilter instance
        """
        return ScenarioFilter(
            universal_only=universal_only,
            exclude_patterns=EXCLUDE_NAME_PATTERNS,
        )

    def filter_by_names(
        self,
        scenarios: List[Scenario],
        names: List[str]
    ) -> List[Scenario]:
        """Filter scenarios by specific names.

        Args:
            scenarios: List of scenarios to filter
            names: List of scenario names to include

        Returns:
            Filtered list of scenarios
        """
        name_set = set(names)
        return [s for s in scenarios if s.name in name_set]

    def process_scenario(
        self,
        scenario: Scenario,
        package_manager_name: str,
        output_base: Path
    ) -> ProcessingResult:
        """Process a single scenario for a package manager.

        Args:
            scenario: Scenario to process
            package_manager_name: Package manager name
            output_base: Base output directory

        Returns:
            ProcessingResult with status and details
        """
        pm = get_package_manager(package_manager_name)

        if pm is None:
            return ProcessingResult(
                scenario_name=scenario.name,
                status=ProcessingStatus.FAILED,
                package_manager=package_manager_name,
                error_message=f"Package manager '{package_manager_name}' not found"
            )

        # Validate scenario compatibility
        if not pm.validate_scenario(scenario):
            return ProcessingResult(
                scenario_name=scenario.name,
                status=ProcessingStatus.SKIPPED,
                package_manager=package_manager_name,
                error_message=f"Scenario not compatible with {package_manager_name}"
            )

        try:
            # Get output directory (hierarchical: output/{pm}/{scenario}/)
            output_dir = pm.get_output_dir(output_base, scenario.name)

            # Generate manifest
            manifest_path = pm.generate_manifest(scenario, output_dir)

            logger.info(f"Generated: {manifest_path}")

            # Log SBOM generation if it exists
            sbom_path = output_dir / "expected.cdx.json"
            if sbom_path.exists():
                logger.info(f"Generated expected SBOM: {sbom_path}")

            return ProcessingResult(
                scenario_name=scenario.name,
                status=ProcessingStatus.SUCCESS,
                package_manager=package_manager_name,
                output_dir=output_dir
            )

        except Exception as e:
            return ProcessingResult(
                scenario_name=scenario.name,
                status=ProcessingStatus.FAILED,
                package_manager=package_manager_name,
                error_message=str(e)
            )

    def execute(
        self,
        package_managers: str,
        scenarios: Optional[str],
        output_dir: Path,
        no_universal_filter: bool
    ) -> int:
        """Execute benchmark generation.

        Args:
            package_managers: Package manager string (e.g., 'uv,pip' or 'all')
            scenarios: Optional comma-separated scenario names
            output_dir: Base output directory
            no_universal_filter: Whether to include non-universal scenarios

        Returns:
            Exit code (0 for success, 1 for error)
        """
        try:
            # Parse package managers
            try:
                pm_list = self.parse_package_managers(package_managers)
            except ValueError as e:
                logger.error(str(e))
                return 1

            # Parse specific scenario names if provided
            scenario_names = None
            if scenarios:
                scenario_names = [s.strip() for s in scenarios.split(",")]

            logger.info(f"Package managers: {', '.join(pm_list)}")
            logger.info("")

            # Process each package manager
            for pm_name in pm_list:
                logger.info(f"=== {pm_name.upper()} ===")

                # Create filter
                filter_config = self.create_filter(
                    universal_only=not no_universal_filter
                )

                # Load scenarios for this package manager
                loaded_scenarios = self.scenario_loader.load_for_package_manager(
                    pm_name,
                    filter_config=filter_config
                )

                if not loaded_scenarios:
                    logger.warning(f"No scenarios found for {pm_name}")
                    logger.info("")
                    continue

                # Filter by specific names if requested
                if scenario_names:
                    loaded_scenarios = self.filter_by_names(loaded_scenarios, scenario_names)

                    if not loaded_scenarios:
                        logger.warning(f"None of the specified scenarios found for {pm_name}")
                        logger.info("")
                        continue

                logger.info(f"Found {len(loaded_scenarios)} scenarios")

                # Create summary
                summary = Summary(
                    total_scenarios=len(loaded_scenarios),
                    package_manager=pm_name,
                    data_source=loaded_scenarios[0].source if loaded_scenarios else None
                )

                # Get package manager instance
                pm = get_package_manager(pm_name)
                if pm is None:
                    logger.error(f"Package manager '{pm_name}' not available")
                    continue

                # Process each scenario
                for scenario in loaded_scenarios:
                    result = self.process_scenario(
                        scenario,
                        pm_name,
                        output_dir
                    )
                    summary.add_processing_result(result)

                    # Log errors
                    if result.status == ProcessingStatus.FAILED:
                        logger.error(f"  {scenario.name}: {result.error_message}")

                # Print summary (lock files are generated automatically)
                summary.print_summary(include_lock=False)
                logger.info("")

            return 0

        except KeyboardInterrupt:
            logger.error("Interrupted by user")
            return 1
        except Exception as e:
            logger.error(f"Error: {e}")
            logger.debug("Traceback:", exc_info=True)
            return 1


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Generate package manager manifests and SBOMs for benchmarking SCA tools."""
    # If no subcommand, invoke 'run' as default
    if ctx.invoked_subcommand is None:
        ctx.invoke(run)


@cli.command(name="run")
@click.option(
    "--pm", "--package-managers",
    "package_managers",
    default=DEFAULT_PACKAGE_MANAGER,
    show_default=True,
    help="Comma-separated list of package managers, or 'all'",
)
@click.option(
    "-s", "--scenarios",
    default=None,
    help="Comma-separated list of specific scenarios",
)
@click.option(
    "-o", "--output-dir",
    type=click.Path(path_type=Path),
    default=OUTPUT_DIR,
    show_default=True,
    help="Base output directory",
)
@click.option(
    "--no-universal-filter",
    is_flag=True,
    help="Include scenarios without universal=true",
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Enable verbose output (DEBUG level)",
)
@click.option(
    "-q", "--quiet",
    is_flag=True,
    help="Show only warnings and errors",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    help="Explicit log level (overrides -v/-q)",
)
def run(package_managers, scenarios, output_dir, no_universal_filter,
        verbose, quiet, log_level):
    """Generate manifests and lock files (default command)."""
    # Validate mutually exclusive flags
    if sum([verbose, quiet, log_level is not None]) > 1:
        raise click.UsageError("--verbose, --quiet, and --log-level are mutually exclusive")

    # Setup logging based on flags
    setup_logging(verbose=verbose, quiet=quiet, log_level=log_level)

    # Execute business logic
    bom_bench_cli = BomBenchCLI()
    exit_code = bom_bench_cli.execute(
        package_managers=package_managers,
        scenarios=scenarios,
        output_dir=output_dir,
        no_universal_filter=no_universal_filter
    )

    raise SystemExit(exit_code)


@cli.command(name="clean")
@click.option("--pm", multiple=True, help="Clean specific package managers only")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted")
def clean(pm, dry_run):
    """Clean output directory (future implementation)."""
    raise click.ClickException("clean command not yet implemented")


@cli.command(name="validate")
@click.argument("sbom_path", type=click.Path(exists=True, path_type=Path))
def validate(sbom_path):
    """Validate SBOM file against schema (future implementation)."""
    raise click.ClickException("validate command not yet implemented")


@cli.command(name="info")
def info():
    """Show configuration and version information (future implementation)."""
    raise click.ClickException("info command not yet implemented")


def main():
    """Entry point for bom-bench command."""
    cli()


if __name__ == "__main__":
    main()
