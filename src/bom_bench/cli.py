"""Command-line interface for bom-bench."""

from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
from rich.live import Live
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.table import Table as ProgressTable

from bom_bench.config import BENCHMARKS_DIR
from bom_bench.console import console, error
from bom_bench.logging import get_logger, setup_logging

load_dotenv()

logger = get_logger(__name__)

app = typer.Typer(
    help="Benchmark SCA tools using fixture-based test scenarios.",
    no_args_is_help=True,
)


LogLevel = Annotated[
    str | None,
    typer.Option(
        "--log-level",
        help="Explicit log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        case_sensitive=False,
    ),
]


def _setup_logging_from_options(verbose: bool, quiet: bool, log_level: str | None) -> None:
    """Configure logging based on CLI options."""
    if sum([verbose, quiet, log_level is not None]) > 1:
        error("--verbose, --quiet, and --log-level are mutually exclusive")
        raise typer.Exit(1)
    setup_logging(verbose=verbose, quiet=quiet, log_level=log_level)


def _parse_comma_list(value: str | None) -> list[str] | None:
    """Parse comma-separated string into list of stripped values."""
    return [item.strip() for item in value.split(",")] if value else None


def _invalidate_fixture_caches(data_dir: Path) -> None:
    """Delete all fixture cache manifests to force regeneration."""
    fixture_cache_dir = data_dir / "fixture_sets"
    if not fixture_cache_dir.exists():
        logger.info("No fixture cache directory found")
        return

    manifests = list(fixture_cache_dir.glob("**/.cache_manifest.json"))
    for cache_manifest in manifests:
        logger.info(f"Deleting cache manifest: {cache_manifest}")
        cache_manifest.unlink()

    if manifests:
        logger.info(f"Invalidated {len(manifests)} fixture cache(s)")
    else:
        logger.info("No fixture caches found to invalidate")


def _validate_tool_selection(
    requested_tools: list[str] | None, registered_tools: dict
) -> list[str]:
    """Validate requested tools exist and return final tool list."""
    if not requested_tools:
        return list(registered_tools.keys())

    for tool in requested_tools:
        if tool not in registered_tools:
            available = ", ".join(registered_tools.keys())
            error(f"Unknown SCA tool: {tool}. Available: {available}")
            raise typer.Exit(1)

    return requested_tools


def _filter_fixtures(fixture_sets: list, fixture_name_list: list[str] | None) -> list:
    """Filter fixtures by name if filter list provided."""
    if not fixture_name_list:
        return fixture_sets
    return [f for f in fixture_sets if f.name in fixture_name_list]


def _create_progress_display() -> tuple:
    """Create progress bar and status display components."""
    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
        console=console,
    )
    progress_task = progress.add_task("Running benchmarks", total=0)

    status_progress = Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        console=console,
    )
    status_task = status_progress.add_task("", total=None)

    layout = ProgressTable.grid()
    layout.add_row(progress)
    layout.add_row(status_progress)

    return layout, progress, progress_task, status_progress, status_task


@app.command()
def benchmark(
    tools: Annotated[
        str | None,
        typer.Option("-t", "--tools", help="Comma-separated SCA tools to run (default: all)"),
    ] = None,
    fixture_sets: Annotated[
        str | None,
        typer.Option("--fixture-sets", help="Comma-separated fixture set names (default: all)"),
    ] = None,
    fixture_names: Annotated[
        str | None,
        typer.Option("-f", "--fixtures", help="Comma-separated specific fixture names to run"),
    ] = None,
    output_dir: Annotated[
        Path,
        typer.Option("-o", "--output-dir", help="Directory for benchmark outputs"),
    ] = BENCHMARKS_DIR,
    refresh_fixtures: Annotated[
        bool,
        typer.Option("--refresh-fixtures", help="Invalidate fixture cache and regenerate"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Enable verbose output (DEBUG level)"),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("-q", "--quiet", help="Show only warnings and errors"),
    ] = False,
    log_level: LogLevel = None,
) -> None:
    """Run SCA tool benchmarking using fixture sets.

    Fixtures define their environment requirements (tools, versions)
    and are executed in isolated sandboxes using mise.

    Example:
        bom-bench benchmark --tools cdxgen,syft --fixture-sets packse
    """
    from bom_bench.config import DATA_DIR
    from bom_bench.fixtures.loader import FixtureSetLoader
    from bom_bench.plugins import initialize_plugins
    from bom_bench.runner import BenchmarkRunner
    from bom_bench.sca_tools import get_registered_tools

    _setup_logging_from_options(verbose, quiet, log_level)
    initialize_plugins()

    if refresh_fixtures:
        _invalidate_fixture_caches(DATA_DIR)

    tool_list = _validate_tool_selection(_parse_comma_list(tools), get_registered_tools())
    if not tool_list:
        error("No SCA tools available. Install plugins or check tool installations.")
        raise typer.Exit(1)

    fixture_set_list = _parse_comma_list(fixture_sets)
    fixture_name_list = _parse_comma_list(fixture_names)

    logger.info(f"SCA Tools: {', '.join(tool_list)}")
    if fixture_set_list:
        logger.info(f"Fixture Sets: {', '.join(fixture_set_list)}")
    if fixture_name_list:
        logger.info(f"Fixtures: {', '.join(fixture_name_list)}")
    logger.info(f"Output dir: {output_dir}")

    loader = FixtureSetLoader()
    all_fixture_sets = loader.load_all()
    if fixture_set_list:
        all_fixture_sets = [fs for fs in all_fixture_sets if fs.name in fixture_set_list]

    if not all_fixture_sets:
        error("No fixture sets found")
        raise typer.Exit(1)

    total_fixtures = sum(
        len(_filter_fixtures(fs.fixtures, fixture_name_list)) for fs in all_fixture_sets
    )
    total_tasks = total_fixtures * len(tool_list)

    layout, progress, progress_task, status_progress, status_task = _create_progress_display()
    progress.update(progress_task, total=total_tasks)

    runner = BenchmarkRunner(output_dir=output_dir)

    def progress_callback(tool_name: str, fixture_set_name: str, fixture_name: str, result):
        """Update progress display after each fixture execution."""
        status_progress.update(
            status_task,
            description=f"[cyan]{tool_name}[/cyan] / {fixture_set_name} / {fixture_name}",
        )
        progress.update(progress_task, advance=1)

    with Live(layout, console=console):
        summaries = runner.run(
            tools=tool_list,
            fixture_sets=fixture_set_list,
            fixtures=fixture_name_list,
            progress_callback=progress_callback,
        )

    console.print()
    for summary in summaries:
        summary.print_summary()

    has_errors = any(summary.sbom_failed > 0 or summary.parse_errors > 0 for summary in summaries)
    raise typer.Exit(1 if has_errors else 0)


@app.command("list-fixtures")
def list_fixtures(
    ecosystem: Annotated[
        str | None,
        typer.Option("--ecosystem", help="Filter by ecosystem (e.g., python, javascript)"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Enable verbose output"),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("-q", "--quiet", help="Show only warnings and errors"),
    ] = False,
    log_level: LogLevel = None,
) -> None:
    """List available fixture sets for benchmarking."""
    from bom_bench.fixtures.loader import FixtureSetLoader
    from bom_bench.plugins import initialize_plugins

    _setup_logging_from_options(verbose, quiet, log_level)
    initialize_plugins()

    loader = FixtureSetLoader()
    fixture_sets = loader.load_by_ecosystem(ecosystem) if ecosystem else loader.load_all()

    if not fixture_sets:
        error("No fixture sets available.")
        console.print("The packse plugin may not be configured correctly.")
        raise typer.Exit(1)

    table = Table(title="Available Fixture Sets")
    table.add_column("Name", style="bold cyan")
    table.add_column("Description", max_width=35)
    table.add_column("Ecosystem")
    table.add_column("Fixtures", justify="right")
    table.add_column("Satisfiable", justify="right")
    table.add_column("Tools")

    for fs in fixture_sets:
        satisfiable = sum(1 for f in fs.fixtures if f.satisfiable)
        unsatisfiable = len(fs.fixtures) - satisfiable
        tool_names = ", ".join(f"{t.name}@{t.version}" for t in fs.environment.tools)

        table.add_row(
            fs.name,
            fs.description or "",
            fs.ecosystem,
            str(len(fs.fixtures)),
            f"{satisfiable} / {unsatisfiable}",
            tool_names,
        )

    console.print(table)


@app.command("list-tools")
def list_tools(
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Enable verbose output"),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("-q", "--quiet", help="Show only warnings and errors"),
    ] = False,
    log_level: LogLevel = None,
) -> None:
    """List available SCA tools from plugins."""
    from bom_bench.plugins import initialize_plugins
    from bom_bench.sca_tools import get_registered_tools

    _setup_logging_from_options(verbose, quiet, log_level)
    initialize_plugins()

    tools = get_registered_tools()

    if not tools:
        error("No SCA tools registered.")
        console.print("Plugins may not be installed correctly.")
        raise typer.Exit(1)

    table = Table(title="Available SCA Tools")
    table.add_column("Name", style="bold cyan")
    table.add_column("Description", max_width=35)
    table.add_column("Ecosystems")
    table.add_column("Dependencies")

    for name, info in sorted(tools.items()):
        tool_deps = ", ".join(f"{t['name']}@{t['version']}" for t in info.tools)
        ecosystems = ", ".join(info.supported_ecosystems)

        table.add_row(
            name,
            info.description or "",
            ecosystems,
            tool_deps,
        )

    console.print(table)


def main() -> None:
    """Entry point for bom-bench command."""
    app()


if __name__ == "__main__":
    main()
