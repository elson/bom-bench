"""Tests for console module."""

from io import StringIO

from rich.console import Console

from bom_bench.console import console, error, success, warning


class TestConsole:
    """Test console instance and helpers."""

    def test_console_is_rich_console(self):
        """Test that console is a Rich Console instance."""
        assert isinstance(console, Console)

    def test_error_prints_red_message(self):
        """Test that error() prints message with error styling."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=True)
        error("Test error message", console=test_console)
        result = output.getvalue()
        assert "Test error message" in result

    def test_success_prints_green_message(self):
        """Test that success() prints message with success styling."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=True)
        success("Test success message", console=test_console)
        result = output.getvalue()
        assert "Test success message" in result

    def test_warning_prints_yellow_message(self):
        """Test that warning() prints message with warning styling."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=True)
        warning("Test warning message", console=test_console)
        result = output.getvalue()
        assert "Test warning message" in result
