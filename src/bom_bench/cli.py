"""Command-line interface for bom-bench."""

from pathlib import Path

import click

from bom_bench.config import (
    BENCHMARKS_DIR,
    DEFAULT_PACKAGE_MANAGER,
    EXCLUDE_NAME_PATTERNS,
    OUTPUT_DIR,
    UNIVERSAL_SCENARIOS_ONLY,
)
from bom_bench.data.loader import ScenarioLoader
from bom_bench.logging_config import get_logger, setup_logging
from bom_bench.models.package_manager import ProcessStatus
from bom_bench.models.result import ProcessingResult, ProcessingStatus, Summary
from bom_bench.models.scenario import Scenario, ScenarioFilter
from bom_bench.package_managers import (
    check_package_manager_available,
    get_package_manager_info,
    list_available_package_managers,
    process_scenario,
)

logger = get_logger(__name__)


class BomBenchCLI:
    """Command-line interface orchestrator for bom-bench."""

    def __init__(self):
        """Initialize CLI orchestrator."""
        self.scenario_loader = ScenarioLoader(auto_fetch=True)

    def parse_package_managers(self, pm_arg: str) -> list[str]:
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
                    f"Unknown package manager: {pm}. Available: {', '.join(available)}"
                )

        return pms

    def create_filter(
        self,
        universal_only: bool = UNIVERSAL_SCENARIOS_ONLY,
        scenario_names: list[str] | None = None,
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

    def filter_by_names(self, scenarios: list[Scenario], names: list[str]) -> list[Scenario]:
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
        self, scenario: Scenario, package_manager_name: str, output_base: Path
    ) -> ProcessingResult:
        """Process a single scenario for a package manager.

        Args:
            scenario: Scenario to process
            package_manager_name: Package manager name
            output_base: Base output directory

        Returns:
            ProcessingResult with status and details
        """
        # Check if PM is available
        if not check_package_manager_available(package_manager_name):
            return ProcessingResult(
                scenario_name=scenario.name,
                status=ProcessingStatus.FAILED,
                package_manager=package_manager_name,
                error_message=f"Package manager '{package_manager_name}' not installed",
            )

        # Check scenario compatibility using PM info
        pm_info = get_package_manager_info(package_manager_name)
        if pm_info is None or scenario.source not in pm_info.supported_sources:
            return ProcessingResult(
                scenario_name=scenario.name,
                status=ProcessingStatus.SKIPPED,
                package_manager=package_manager_name,
                error_message=f"Scenario source '{scenario.source}' not compatible with {package_manager_name}",
            )

        try:
            # Calculate output directory (standard pattern: output/scenarios/{pm}/{scenario}/)
            output_dir = output_base / "scenarios" / package_manager_name / scenario.name

            # Process scenario using new atomic operation
            result = process_scenario(package_manager_name, scenario, output_dir)

            if result is None:
                return ProcessingResult(
                    scenario_name=scenario.name,
                    status=ProcessingStatus.FAILED,
                    package_manager=package_manager_name,
                    error_message=f"No plugin handled processing for PM '{package_manager_name}'",
                )

            # Log generated files
            if result.manifest_path:
                logger.info(f"Generated: {result.manifest_path}")
            if result.sbom_path:
                logger.info(f"Generated expected SBOM: {result.sbom_path}")

            # Convert ProcessScenarioResult to ProcessingResult
            if result.status == ProcessStatus.SUCCESS:
                return ProcessingResult(
                    scenario_name=scenario.name,
                    status=ProcessingStatus.SUCCESS,
                    package_manager=package_manager_name,
                    output_dir=output_dir,
                )
            else:
                return ProcessingResult(
                    scenario_name=scenario.name,
                    status=ProcessingStatus.FAILED,
                    package_manager=package_manager_name,
                    error_message=result.error_message
                    or f"Processing failed with status: {result.status.value}",
                )

        except Exception as e:
            return ProcessingResult(
                scenario_name=scenario.name,
                status=ProcessingStatus.FAILED,
                package_manager=package_manager_name,
                error_message=str(e),
            )

    def execute(
        self,
        package_managers: str,
        scenarios: str | None,
        output_dir: Path,
        no_universal_filter: bool,
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
                filter_config = self.create_filter(universal_only=not no_universal_filter)

                # Load scenarios for this package manager
                loaded_scenarios = self.scenario_loader.load_for_package_manager(
                    pm_name, filter_config=filter_config
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
                    data_source=loaded_scenarios[0].source if loaded_scenarios else None,
                )

                # Process each scenario
                for scenario in loaded_scenarios:
                    result = self.process_scenario(scenario, pm_name, output_dir)
                    summary.add_processing_result(result)

                    # Log errors
                    if result.status == ProcessingStatus.FAILED:
                        logger.error(f"  {scenario.name}: {result.error_message}")

                # Print summary
                summary.print_summary()
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
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose output (DEBUG level)",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Show only warnings and errors",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    help="Explicit log level (overrides -v/-q)",
)
@click.pass_context
def cli(ctx, verbose, quiet, log_level):
    """Generate package manager manifests and SBOMs for benchmarking SCA tools."""
    # Validate mutually exclusive flags
    if sum([verbose, quiet, log_level is not None]) > 1:
        raise click.UsageError("--verbose, --quiet, and --log-level are mutually exclusive")

    # Setup logging based on flags
    setup_logging(verbose=verbose, quiet=quiet, log_level=log_level)

    # If no subcommand, invoke 'setup' as default
    if ctx.invoked_subcommand is None:
        ctx.invoke(setup)


@cli.command(name="setup")
@click.option(
    "--pm",
    "--package-managers",
    "package_managers",
    default=DEFAULT_PACKAGE_MANAGER,
    show_default=True,
    help="Comma-separated list of package managers, or 'all'",
)
@click.option(
    "-s",
    "--scenarios",
    default=None,
    help="Comma-separated list of specific scenarios",
)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(path_type=Path),  # type: ignore[type-var]
    default=OUTPUT_DIR,
    show_default=True,
    help="Base output directory",
)
@click.option(
    "--no-universal-filter",
    is_flag=True,
    help="Include scenarios without universal=true",
)
def setup(package_managers, scenarios, output_dir, no_universal_filter):
    """Generate manifests, lock files, and expected SBOMs."""
    # Execute business logic
    bom_bench_cli = BomBenchCLI()
    exit_code = bom_bench_cli.execute(
        package_managers=package_managers,
        scenarios=scenarios,
        output_dir=output_dir,
        no_universal_filter=no_universal_filter,
    )

    raise SystemExit(exit_code)


# Keep 'run' as an alias for backward compatibility
@cli.command(name="run", hidden=True)
@click.option("--pm", "--package-managers", "package_managers", default=DEFAULT_PACKAGE_MANAGER)
@click.option("-s", "--scenarios", default=None)
@click.option("-o", "--output-dir", type=click.Path(path_type=Path), default=OUTPUT_DIR)  # type: ignore[type-var]
@click.option("--no-universal-filter", is_flag=True)
@click.pass_context
def run(ctx, **kwargs):
    """Generate manifests and lock files (deprecated, use 'setup')."""
    logger.warning("'bom-bench run' is deprecated, use 'bom-bench setup' instead")
    ctx.invoke(setup, **kwargs)


@cli.command(name="benchmark")
@click.option(
    "--pm",
    "--package-managers",
    "package_managers",
    default=DEFAULT_PACKAGE_MANAGER,
    show_default=True,
    help="Comma-separated list of package managers, or 'all'",
)
@click.option(
    "-t",
    "--tools",
    default=None,
    help="Comma-separated SCA tools to run (default: all available)",
)
@click.option(
    "-s",
    "--scenarios",
    default=None,
    help="Comma-separated list of specific scenarios",
)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(path_type=Path),  # type: ignore[type-var]
    default=OUTPUT_DIR,
    show_default=True,
    help="Directory containing generated projects from setup",
)
@click.option(
    "--benchmarks-dir",
    type=click.Path(path_type=Path),  # type: ignore[type-var]
    default=BENCHMARKS_DIR,
    show_default=True,
    help="Directory for benchmark outputs",
)
def benchmark(package_managers, tools, scenarios, output_dir, benchmarks_dir):
    """Run SCA tool benchmarking against generated projects.

    Prerequisites:
    - Run 'bom-bench setup' first to generate projects
    - Install SCA tools (e.g., npm install -g @cyclonedx/cdxgen)

    Example:
        bom-bench benchmark --pm uv --tools cdxgen
    """
    from bom_bench.benchmarking.runner import BenchmarkRunner
    from bom_bench.plugins import initialize_plugins
    from bom_bench.sca_tools import (
        check_tool_available,
        get_registered_tools,
        list_available_tools,
    )

    # Initialize plugin system
    initialize_plugins()

    # Determine which tools to run
    if tools:
        tool_list = [t.strip() for t in tools.split(",")]
        registered = get_registered_tools()
        for tool in tool_list:
            if tool not in registered:
                raise click.ClickException(
                    f"Unknown SCA tool: {tool}. Available: {', '.join(registered.keys())}"
                )
    else:
        tool_list = list_available_tools()

    if not tool_list:
        raise click.ClickException(
            "No SCA tools available. Install plugins or check tool installations."
        )

    # Check tool availability and warn
    unavailable = []
    for tool in tool_list:
        if not check_tool_available(tool):
            unavailable.append(tool)

    if unavailable:
        logger.warning(f"Tools not installed: {', '.join(unavailable)}")
        logger.warning("Install them or they will be skipped")

    # Parse scenarios if provided
    scenario_list = None
    if scenarios:
        scenario_list = [s.strip() for s in scenarios.split(",")]

    # Log configuration
    logger.info(f"SCA Tools: {', '.join(tool_list)}")
    logger.info(f"Output dir: {output_dir}")
    logger.info(f"Benchmarks dir: {benchmarks_dir}")
    logger.info("")

    # Create and run benchmark runner
    runner = BenchmarkRunner(output_dir=output_dir, benchmarks_dir=benchmarks_dir, tools=tool_list)

    exit_code = runner.run(package_managers=package_managers, scenarios=scenario_list)

    raise SystemExit(exit_code)


@cli.command(name="list-tools")
@click.option(
    "--check",
    is_flag=True,
    help="Check if tools are installed",
)
def list_tools(check):
    """List available SCA tools from plugins."""
    from bom_bench.plugins import initialize_plugins
    from bom_bench.sca_tools import (
        check_tool_available,
        get_registered_tools,
    )

    # Initialize plugin system
    initialize_plugins()

    tools = get_registered_tools()

    if not tools:
        click.echo("No SCA tools registered.")
        click.echo("Plugins may not be installed correctly.")
        raise SystemExit(1)

    click.echo("Available SCA Tools:")
    click.echo("")

    for name, info in sorted(tools.items()):
        status = ""
        if check:
            available = check_tool_available(name)
            status = (
                click.style(" [installed]", fg="green")
                if available
                else click.style(" [not found]", fg="red")
            )

        click.echo(f"  {click.style(name, bold=True)}{status}")

        if info.description:
            click.echo(f"    {info.description}")

        if info.version:
            click.echo(f"    Version: {info.version}")

        if info.supported_ecosystems:
            click.echo(f"    Ecosystems: {', '.join(info.supported_ecosystems)}")

        if info.homepage:
            click.echo(f"    Homepage: {info.homepage}")

        click.echo("")


@cli.command(name="clean")
@click.option("--pm", multiple=True, help="Clean specific package managers only")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted")
def clean(pm, dry_run):
    """Clean output directory (future implementation)."""
    raise click.ClickException("clean command not yet implemented")


@cli.command(name="validate")
@click.argument("sbom_path", type=click.Path(exists=True, path_type=Path))  # type: ignore[type-var]
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
