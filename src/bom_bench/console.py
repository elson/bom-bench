"""Shared Rich console for bom-bench CLI output."""

from rich.console import Console

console = Console()


def error(message: str, console: Console = console) -> None:
    """Print an error message in red."""
    console.print(f"[red bold]{message}[/red bold]")


def success(message: str, console: Console = console) -> None:
    """Print a success message in green."""
    console.print(f"[green]{message}[/green]")


def warning(message: str, console: Console = console) -> None:
    """Print a warning message in yellow."""
    console.print(f"[yellow]{message}[/yellow]")
