"""Tests for CLI commands."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from bom_bench.cli import (
    _create_progress_display,
    _filter_fixtures,
    _invalidate_fixture_caches,
    _parse_comma_list,
    _validate_tool_selection,
    app,
    main,
)

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
    @patch("bom_bench.sca_tools.get_registered_tools")
    def test_benchmark_no_tools_error(self, mock_get_tools, mock_init):
        """Test that benchmark shows error when no tools available."""
        mock_get_tools.return_value = {}

        result = runner.invoke(app, ["benchmark"])
        assert result.exit_code == 1
        assert "No SCA tools available" in result.stdout

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.sca_tools.get_registered_tools")
    @patch("bom_bench.fixtures.loader.FixtureSetLoader")
    def test_benchmark_no_fixture_sets_error(self, mock_loader_class, mock_get_tools, mock_init):
        """Test that benchmark shows error when no fixture sets available."""
        mock_get_tools.return_value = {"cdxgen": MagicMock()}

        mock_loader = MagicMock()
        mock_loader.load_all.return_value = []
        mock_loader_class.return_value = mock_loader

        result = runner.invoke(app, ["benchmark"])
        assert result.exit_code == 1
        assert "No fixture sets found" in result.stdout

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.sca_tools.get_registered_tools")
    @patch("bom_bench.fixtures.loader.FixtureSetLoader")
    def test_benchmark_with_fixture_set_filter(self, mock_loader_class, mock_get_tools, mock_init):
        """Test that benchmark filters fixture sets correctly."""
        mock_get_tools.return_value = {"cdxgen": MagicMock()}

        mock_loader = MagicMock()
        mock_loader.load_all.return_value = []
        mock_loader_class.return_value = mock_loader

        result = runner.invoke(app, ["benchmark", "--fixture-sets", "packse"])
        assert result.exit_code == 1
        assert "No fixture sets found" in result.stdout

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.sca_tools.get_registered_tools")
    @patch("bom_bench.fixtures.loader.FixtureSetLoader")
    def test_benchmark_with_fixtures_filter(self, mock_loader_class, mock_get_tools, mock_init):
        """Test that benchmark filters specific fixtures correctly."""
        mock_get_tools.return_value = {"cdxgen": MagicMock()}

        mock_loader = MagicMock()
        mock_loader.load_all.return_value = []
        mock_loader_class.return_value = mock_loader

        result = runner.invoke(app, ["benchmark", "--fixtures", "fork-basic"])
        assert result.exit_code == 1
        assert "No fixture sets found" in result.stdout

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.sca_tools.get_registered_tools")
    @patch("bom_bench.sca_tools.get_tool_config")
    @patch("bom_bench.fixtures.loader.FixtureSetLoader")
    @patch("bom_bench.runner.BenchmarkRunner")
    def test_benchmark_successful_run(
        self, mock_runner_class, mock_loader_class, mock_get_config, mock_get_tools, mock_init
    ):
        """Test successful benchmark execution."""
        mock_get_tools.return_value = {"cdxgen": MagicMock()}
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_fixture = MagicMock()
        mock_fixture.name = "test-fixture"
        mock_fixture.satisfiable = True

        mock_env = MagicMock()
        mock_fs = MagicMock()
        mock_fs.name = "test-set"
        mock_fs.fixtures = [mock_fixture]
        mock_fs.environment = mock_env

        mock_loader = MagicMock()
        mock_loader.load_all.return_value = [mock_fs]
        mock_loader_class.return_value = mock_loader

        mock_result = MagicMock()
        mock_result.success = True

        mock_executor = MagicMock()
        mock_executor.execute.return_value = mock_result

        mock_runner = MagicMock()
        mock_runner.executor = mock_executor
        mock_runner_class.return_value = mock_runner

        mock_summary = MagicMock()
        mock_summary.sbom_failed = 0
        mock_summary.parse_errors = 0

        with patch("bom_bench.models.sca_tool.BenchmarkSummary") as mock_summary_class:
            mock_summary_instance = MagicMock()
            mock_summary_instance.sbom_failed = 0
            mock_summary_instance.parse_errors = 0
            mock_summary_class.return_value = mock_summary_instance

            result = runner.invoke(app, ["benchmark"])

            assert result.exit_code == 0
            mock_executor.execute.assert_called_once()
            mock_summary_instance.add_result.assert_called_once_with(mock_result)
            mock_summary_instance.calculate_aggregates.assert_called_once()

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.sca_tools.get_registered_tools")
    @patch("bom_bench.sca_tools.get_tool_config")
    @patch("bom_bench.fixtures.loader.FixtureSetLoader")
    @patch("bom_bench.runner.BenchmarkRunner")
    def test_benchmark_with_errors(
        self, mock_runner_class, mock_loader_class, mock_get_config, mock_get_tools, mock_init
    ):
        """Test benchmark execution with errors exits with code 1."""
        mock_get_tools.return_value = {"cdxgen": MagicMock()}
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_fixture = MagicMock()
        mock_fixture.name = "test-fixture"
        mock_fixture.satisfiable = True

        mock_env = MagicMock()
        mock_fs = MagicMock()
        mock_fs.name = "test-set"
        mock_fs.fixtures = [mock_fixture]
        mock_fs.environment = mock_env

        mock_loader = MagicMock()
        mock_loader.load_all.return_value = [mock_fs]
        mock_loader_class.return_value = mock_loader

        mock_result = MagicMock()
        mock_result.success = False

        mock_executor = MagicMock()
        mock_executor.execute.return_value = mock_result

        mock_runner = MagicMock()
        mock_runner.executor = mock_executor
        mock_runner_class.return_value = mock_runner

        with patch("bom_bench.models.sca_tool.BenchmarkSummary") as mock_summary_class:
            mock_summary_instance = MagicMock()
            mock_summary_instance.sbom_failed = 1
            mock_summary_instance.parse_errors = 0
            mock_summary_class.return_value = mock_summary_instance

            result = runner.invoke(app, ["benchmark"])

            assert result.exit_code == 1

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.sca_tools.get_registered_tools")
    @patch("bom_bench.fixtures.loader.FixtureSetLoader")
    def test_benchmark_refresh_fixtures(self, mock_loader_class, mock_get_tools, mock_init):
        """Test benchmark with --refresh-fixtures flag."""
        mock_get_tools.return_value = {"cdxgen": MagicMock()}
        mock_loader = MagicMock()
        mock_loader.load_all.return_value = []
        mock_loader_class.return_value = mock_loader

        with patch("bom_bench.cli._invalidate_fixture_caches") as mock_invalidate:
            result = runner.invoke(app, ["benchmark", "--refresh-fixtures"])
            assert result.exit_code == 1
            mock_invalidate.assert_called_once()

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.sca_tools.get_registered_tools")
    @patch("bom_bench.sca_tools.get_tool_config")
    @patch("bom_bench.fixtures.loader.FixtureSetLoader")
    @patch("bom_bench.runner.BenchmarkRunner")
    def test_benchmark_tool_config_none(
        self, mock_runner_class, mock_loader_class, mock_get_config, mock_get_tools, mock_init
    ):
        """Test benchmark when tool config is None."""
        mock_get_tools.return_value = {"cdxgen": MagicMock()}
        mock_get_config.return_value = None

        mock_fixture = MagicMock()
        mock_fixture.name = "test-fixture"
        mock_env = MagicMock()
        mock_fs = MagicMock()
        mock_fs.name = "test-set"
        mock_fs.fixtures = [mock_fixture]
        mock_fs.environment = mock_env

        mock_loader = MagicMock()
        mock_loader.load_all.return_value = [mock_fs]
        mock_loader_class.return_value = mock_loader

        mock_executor = MagicMock()
        mock_runner = MagicMock()
        mock_runner.executor = mock_executor
        mock_runner_class.return_value = mock_runner

        runner.invoke(app, ["benchmark"])

        mock_executor.execute.assert_not_called()

    @patch("bom_bench.plugins.initialize_plugins")
    @patch("bom_bench.sca_tools.get_registered_tools")
    @patch("bom_bench.sca_tools.get_tool_config")
    @patch("bom_bench.fixtures.loader.FixtureSetLoader")
    @patch("bom_bench.runner.BenchmarkRunner")
    def test_benchmark_no_matching_fixtures_after_filter(
        self, mock_runner_class, mock_loader_class, mock_get_config, mock_get_tools, mock_init
    ):
        """Test benchmark when fixture filter matches no fixtures in a set."""
        mock_get_tools.return_value = {"cdxgen": MagicMock()}
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_fixture = MagicMock()
        mock_fixture.name = "other-fixture"
        mock_env = MagicMock()
        mock_fs = MagicMock()
        mock_fs.name = "test-set"
        mock_fs.fixtures = [mock_fixture]
        mock_fs.environment = mock_env

        mock_loader = MagicMock()
        mock_loader.load_all.return_value = [mock_fs]
        mock_loader_class.return_value = mock_loader

        mock_executor = MagicMock()
        mock_runner = MagicMock()
        mock_runner.executor = mock_executor
        mock_runner_class.return_value = mock_runner

        runner.invoke(app, ["benchmark", "--fixtures", "non-matching-fixture"])

        mock_executor.execute.assert_not_called()


class TestHelperFunctions:
    """Test CLI helper functions."""

    def test_parse_comma_list_with_values(self):
        """Test parsing comma-separated values."""
        result = _parse_comma_list("foo,bar,baz")
        assert result == ["foo", "bar", "baz"]

    def test_parse_comma_list_with_spaces(self):
        """Test parsing comma-separated values with spaces."""
        result = _parse_comma_list("  foo  ,  bar  ,  baz  ")
        assert result == ["foo", "bar", "baz"]

    def test_parse_comma_list_none(self):
        """Test parsing None returns None."""
        result = _parse_comma_list(None)
        assert result is None

    def test_invalidate_fixture_caches_no_directory(self, tmp_path):
        """Test cache invalidation when directory doesn't exist."""
        data_dir = tmp_path / "nonexistent"
        _invalidate_fixture_caches(data_dir)

    def test_invalidate_fixture_caches_no_manifests(self, tmp_path):
        """Test cache invalidation with no cache manifests."""
        fixture_cache_dir = tmp_path / "fixture_sets"
        fixture_cache_dir.mkdir(parents=True)
        _invalidate_fixture_caches(tmp_path)

    def test_invalidate_fixture_caches_with_manifests(self, tmp_path):
        """Test cache invalidation deletes manifests."""
        fixture_cache_dir = tmp_path / "fixture_sets" / "packse"
        fixture_cache_dir.mkdir(parents=True)
        manifest1 = fixture_cache_dir / ".cache_manifest.json"
        manifest1.write_text("{}")

        nested_dir = fixture_cache_dir / "subdir"
        nested_dir.mkdir()
        manifest2 = nested_dir / ".cache_manifest.json"
        manifest2.write_text("{}")

        _invalidate_fixture_caches(tmp_path)

        assert not manifest1.exists()
        assert not manifest2.exists()

    def test_validate_tool_selection_none_requested(self):
        """Test tool validation with no tools requested returns all."""
        registered = {"cdxgen": MagicMock(), "syft": MagicMock()}
        result = _validate_tool_selection(None, registered)
        assert set(result) == {"cdxgen", "syft"}

    def test_validate_tool_selection_valid_tools(self):
        """Test tool validation with valid requested tools."""
        registered = {"cdxgen": MagicMock(), "syft": MagicMock()}
        result = _validate_tool_selection(["cdxgen"], registered)
        assert result == ["cdxgen"]

    def test_validate_tool_selection_invalid_tool(self):
        """Test tool validation raises error for invalid tool."""
        import pytest
        from click.exceptions import Exit

        registered = {"cdxgen": MagicMock()}
        with pytest.raises(Exit) as exc_info:
            _validate_tool_selection(["unknown"], registered)
        assert exc_info.value.exit_code == 1

    def test_filter_fixtures_no_filter(self):
        """Test fixture filtering with no filter returns all."""
        fixture1 = MagicMock()
        fixture1.name = "test1"
        fixture2 = MagicMock()
        fixture2.name = "test2"
        fixtures = [fixture1, fixture2]

        result = _filter_fixtures(fixtures, None)
        assert result == fixtures

    def test_filter_fixtures_with_filter(self):
        """Test fixture filtering with name filter."""
        fixture1 = MagicMock()
        fixture1.name = "test1"
        fixture2 = MagicMock()
        fixture2.name = "test2"
        fixtures = [fixture1, fixture2]

        result = _filter_fixtures(fixtures, ["test1"])
        assert result == [fixture1]

    def test_create_progress_display(self):
        """Test progress display creation."""
        layout, progress, progress_task, status_progress, status_task = _create_progress_display()

        assert layout is not None
        assert progress is not None
        assert status_progress is not None
        assert isinstance(progress_task, int)
        assert isinstance(status_task, int)


class TestMainEntryPoint:
    """Test main entry point."""

    @patch("bom_bench.cli.app")
    def test_main_calls_app(self, mock_app):
        """Test main() calls the Typer app."""
        main()
        mock_app.assert_called_once()
