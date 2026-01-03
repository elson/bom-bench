"""Command-line interface for bom-bench."""

from pathlib import Path

import click

from bom_bench.config import BENCHMARKS_DIR
from bom_bench.logging import get_logger, setup_logging

logger = get_logger(__name__)


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
    """Benchmark SCA tools using fixture-based test scenarios."""
    if sum([verbose, quiet, log_level is not None]) > 1:
        raise click.UsageError("--verbose, --quiet, and --log-level are mutually exclusive")

    setup_logging(verbose=verbose, quiet=quiet, log_level=log_level)

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command(name="benchmark")
@click.option(
    "-t",
    "--tools",
    default=None,
    help="Comma-separated SCA tools to run (default: all available)",
)
@click.option(
    "--fixture-sets",
    default=None,
    help="Comma-separated fixture set names (default: all)",
)
@click.option(
    "-f",
    "--fixtures",
    "fixture_names",
    default=None,
    help="Comma-separated specific fixture names to run",
)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(path_type=Path),  # type: ignore[type-var]
    default=BENCHMARKS_DIR,
    show_default=True,
    help="Directory for benchmark outputs",
)
def benchmark(tools, fixture_sets, fixture_names, output_dir):
    """Run SCA tool benchmarking using fixture sets.

    Fixtures define their environment requirements (tools, versions)
    and are executed in isolated sandboxes using mise.

    Example:
        bom-bench benchmark --tools cdxgen,syft --fixture-sets packse
    """
    from bom_bench.plugins import initialize_plugins
    from bom_bench.runner import BenchmarkRunner
    from bom_bench.sca_tools import (
        check_tool_available,
        get_registered_tools,
        list_available_tools,
    )

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

    # Parse fixture sets and names
    fixture_set_list = None
    if fixture_sets:
        fixture_set_list = [fs.strip() for fs in fixture_sets.split(",")]

    fixture_name_list = None
    if fixture_names:
        fixture_name_list = [f.strip() for f in fixture_names.split(",")]

    # Log configuration
    logger.info(f"SCA Tools: {', '.join(tool_list)}")
    if fixture_set_list:
        logger.info(f"Fixture Sets: {', '.join(fixture_set_list)}")
    if fixture_name_list:
        logger.info(f"Fixtures: {', '.join(fixture_name_list)}")
    logger.info(f"Output dir: {output_dir}")
    logger.info("")

    # Create and run benchmark runner
    runner = BenchmarkRunner(output_dir=output_dir)
    summaries = runner.run(
        tools=tool_list,
        fixture_sets=fixture_set_list,
        fixtures=fixture_name_list,
    )

    # Determine exit code
    has_errors = any(summary.sbom_failed > 0 or summary.parse_errors > 0 for summary in summaries)

    raise SystemExit(1 if has_errors else 0)


@cli.command(name="list-fixtures")
@click.option(
    "--ecosystem",
    default=None,
    help="Filter by ecosystem (e.g., python, javascript)",
)
def list_fixtures(ecosystem):
    """List available fixture sets for benchmarking."""
    from bom_bench.fixtures.loader import FixtureSetLoader
    from bom_bench.plugins import initialize_plugins

    initialize_plugins()

    loader = FixtureSetLoader()
    fixture_sets = loader.load_by_ecosystem(ecosystem) if ecosystem else loader.load_all()

    if not fixture_sets:
        click.echo("No fixture sets available.")
        click.echo("The packse plugin may not be configured correctly.")
        raise SystemExit(1)

    click.echo("Available Fixture Sets:")
    click.echo("")

    for fs in fixture_sets:
        click.echo(f"  {click.style(fs.name, bold=True)}")
        if fs.description:
            click.echo(f"    {fs.description}")
        click.echo(f"    Ecosystem: {fs.ecosystem}")
        click.echo(f"    Fixtures: {len(fs.fixtures)}")

        satisfiable = sum(1 for f in fs.fixtures if f.satisfiable)
        unsatisfiable = len(fs.fixtures) - satisfiable
        click.echo(f"    Satisfiable: {satisfiable}, Unsatisfiable: {unsatisfiable}")

        if fs.environment.tools:
            tool_names = [f"{t.name}@{t.version}" for t in fs.environment.tools]
            click.echo(f"    Tools: {', '.join(tool_names)}")

        click.echo("")


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


def main():
    """Entry point for bom-bench command."""
    cli()


if __name__ == "__main__":
    main()
