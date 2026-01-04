"""Tests for CLI commands."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from bom_bench.cli import app

runner = CliRunner()


class TestCLIHelp:
    """Test CLI help output."""

    def test_main_help(self):
        """Test main help displays commands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "benchmark" in result.stdout
        assert "list-fixtures" in result.stdout
        assert "list-tools" in result.stdout

    def test_benchmark_help(self):
        """Test benchmark command help."""
        result = runner.invoke(app, ["benchmark", "--help"])
        assert result.exit_code == 0
        assert "--tools" in result.stdout
        assert "--fixture-sets" in result.stdout
        assert "--fixtures" in result.stdout
        assert "--output-dir" in result.stdout

    def test_list_fixtures_help(self):
        """Test list-fixtures command help."""
        result = runner.invoke(app, ["list-fixtures", "--help"])
        assert result.exit_code == 0
        assert "--ecosystem" in result.stdout

    def test_list_tools_help(self):
        """Test list-tools command help."""
        result = runner.invoke(app, ["list-tools", "--help"])
        assert result.exit_code == 0
        assert "--verbose" in result.stdout
        assert "--quiet" in result.stdout


class TestLoggingOptions:
    """Test logging option validation."""

    def test_mutually_exclusive_verbose_quiet(self):
        """Test that --verbose and --quiet are mutually exclusive."""
        result = runner.invoke(app, ["list-tools", "--verbose", "--quiet"])
        assert result.exit_code == 1
        assert "mutually exclusive" in result.stdout

    def test_mutually_exclusive_verbose_log_level(self):
        """Test that --verbose and --log-level are mutually exclusive."""
        result = runner.invoke(app, ["list-tools", "--verbose", "--log-level", "DEBUG"])
        assert result.exit_code == 1
        assert "mutually exclusive" in result.stdout

    def test_mutually_exclusive_quiet_log_level(self):
        """Test that --quiet and --log-level are mutually exclusive."""
        result = runner.invoke(app, ["list-tools", "--quiet", "--log-level", "WARNING"])
        assert result.exit_code == 1
        assert "mutually exclusive" in result.stdout


class TestListTools:
    """Test list-tools command."""

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.sca_tools.get_registered_tools")
    def test_list_tools_displays_table(self, mock_get_tools, mock_init):
        """Test that list-tools displays a Rich table."""
        mock_info = MagicMock()
        mock_info.description = "Test tool"
        mock_info.supported_ecosystems = ["python"]
        mock_info.tools = [{"name": "node", "version": "22"}]

        mock_get_tools.return_value = {"test-tool": mock_info}

        result = runner.invoke(app, ["list-tools"])
        assert result.exit_code == 0
        assert "test-tool" in result.stdout
        assert "Test tool" in result.stdout
        assert "python" in result.stdout

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.sca_tools.get_registered_tools")
    def test_list_tools_no_tools_error(self, mock_get_tools, mock_init):
        """Test that list-tools shows error when no tools available."""
        mock_get_tools.return_value = {}

        result = runner.invoke(app, ["list-tools"])
        assert result.exit_code == 1
        assert "No SCA tools registered" in result.stdout


class TestListFixtures:
    """Test list-fixtures command."""

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.fixtures.loader.FixtureSetLoader")
    def test_list_fixtures_displays_table(self, mock_loader_class, mock_init):
        """Test that list-fixtures displays a Rich table."""
        mock_fixture = MagicMock()
        mock_fixture.satisfiable = True

        mock_env = MagicMock()
        mock_env.tools = []

        mock_fs = MagicMock()
        mock_fs.name = "test-set"
        mock_fs.description = "Test fixture set"
        mock_fs.ecosystem = "python"
        mock_fs.fixtures = [mock_fixture]
        mock_fs.environment = mock_env

        mock_loader = MagicMock()
        mock_loader.load_all.return_value = [mock_fs]
        mock_loader_class.return_value = mock_loader

        result = runner.invoke(app, ["list-fixtures"])
        assert result.exit_code == 0
        assert "test-set" in result.stdout
        assert "python" in result.stdout

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.fixtures.loader.FixtureSetLoader")
    def test_list_fixtures_no_fixtures_error(self, mock_loader_class, mock_init):
        """Test that list-fixtures shows error when no fixtures available."""
        mock_loader = MagicMock()
        mock_loader.load_all.return_value = []
        mock_loader_class.return_value = mock_loader

        result = runner.invoke(app, ["list-fixtures"])
        assert result.exit_code == 1
        assert "No fixture sets available" in result.stdout

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.fixtures.loader.FixtureSetLoader")
    def test_list_fixtures_with_ecosystem_filter(self, mock_loader_class, mock_init):
        """Test that list-fixtures filters by ecosystem."""
        mock_fixture = MagicMock()
        mock_fixture.satisfiable = True

        mock_env = MagicMock()
        mock_env.tools = []

        mock_fs = MagicMock()
        mock_fs.name = "test-set"
        mock_fs.description = "Test fixture set"
        mock_fs.ecosystem = "python"
        mock_fs.fixtures = [mock_fixture]
        mock_fs.environment = mock_env

        mock_loader = MagicMock()
        mock_loader.load_by_ecosystem.return_value = [mock_fs]
        mock_loader_class.return_value = mock_loader

        result = runner.invoke(app, ["list-fixtures", "--ecosystem", "python"])
        assert result.exit_code == 0
        mock_loader.load_by_ecosystem.assert_called_once_with("python")


class TestBenchmark:
    """Test benchmark command."""

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.sca_tools.get_registered_tools")
    def test_benchmark_unknown_tool_error(self, mock_get_tools, mock_init):
        """Test that benchmark shows error for unknown tool."""
        mock_get_tools.return_value = {"cdxgen": MagicMock()}

        result = runner.invoke(app, ["benchmark", "--tools", "unknown-tool"])
        assert result.exit_code == 1
        assert "Unknown SCA tool: unknown-tool" in result.stdout

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.sca_tools.list_available_tools")
    def test_benchmark_no_tools_error(self, mock_list_tools, mock_init):
        """Test that benchmark shows error when no tools available."""
        mock_list_tools.return_value = []

        result = runner.invoke(app, ["benchmark"])
        assert result.exit_code == 1
        assert "No SCA tools available" in result.stdout

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.sca_tools.list_available_tools")
    @patch("bom_bench.fixtures.loader.FixtureSetLoader")
    def test_benchmark_no_fixture_sets_error(self, mock_loader_class, mock_list_tools, mock_init):
        """Test that benchmark shows error when no fixture sets available."""
        mock_list_tools.return_value = ["cdxgen"]

        mock_loader = MagicMock()
        mock_loader.load_all.return_value = []
        mock_loader_class.return_value = mock_loader

        result = runner.invoke(app, ["benchmark"])
        assert result.exit_code == 1
        assert "No fixture sets found" in result.stdout

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.sca_tools.list_available_tools")
    @patch("bom_bench.fixtures.loader.FixtureSetLoader")
    def test_benchmark_with_fixture_set_filter(self, mock_loader_class, mock_list_tools, mock_init):
        """Test that benchmark filters fixture sets correctly."""
        mock_list_tools.return_value = ["cdxgen"]

        mock_loader = MagicMock()
        mock_loader.load_all.return_value = []
        mock_loader_class.return_value = mock_loader

        result = runner.invoke(app, ["benchmark", "--fixture-sets", "packse"])
        assert result.exit_code == 1
        assert "No fixture sets found" in result.stdout

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.sca_tools.list_available_tools")
    @patch("bom_bench.fixtures.loader.FixtureSetLoader")
    def test_benchmark_with_fixtures_filter(self, mock_loader_class, mock_list_tools, mock_init):
        """Test that benchmark filters specific fixtures correctly."""
        mock_list_tools.return_value = ["cdxgen"]

        mock_loader = MagicMock()
        mock_loader.load_all.return_value = []
        mock_loader_class.return_value = mock_loader

        result = runner.invoke(app, ["benchmark", "--fixtures", "fork-basic"])
        assert result.exit_code == 1
        assert "No fixture sets found" in result.stdout
