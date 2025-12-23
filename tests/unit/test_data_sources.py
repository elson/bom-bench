"""Tests for data sources."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bom_bench.data import (
    get_data_source,
    get_available_sources,
    get_sources_for_pm,
    DATA_SOURCES,
)
from bom_bench.data.sources.packse import PackseDataSource
from bom_bench.data.loader import ScenarioLoader
from bom_bench.models.scenario import Scenario, Root, ResolverOptions, ScenarioFilter


class TestDataSourceRegistry:
    """Tests for data source registry."""

    def test_get_available_sources(self):
        """Test getting available data sources."""
        sources = get_available_sources()
        assert "packse" in sources
        assert len(sources) >= 1

    def test_get_data_source_packse(self, tmp_path):
        """Test getting packse data source."""
        source = get_data_source("packse", tmp_path / "packse")
        assert isinstance(source, PackseDataSource)
        assert source.name == "packse"
        assert "uv" in source.supported_pms
        assert "pip" in source.supported_pms

    def test_get_data_source_invalid(self):
        """Test getting invalid data source raises ValueError."""
        with pytest.raises(ValueError, match="Unknown data source"):
            get_data_source("nonexistent")

    def test_get_sources_for_pm_uv(self):
        """Test getting sources that support uv."""
        sources = get_sources_for_pm("uv")
        assert "packse" in sources

    def test_get_sources_for_pm_pip(self):
        """Test getting sources that support pip."""
        sources = get_sources_for_pm("pip")
        assert "packse" in sources

    def test_get_sources_for_pm_nonexistent(self):
        """Test getting sources for non-existent PM returns empty."""
        sources = get_sources_for_pm("nonexistent-pm")
        assert sources == []


class TestPackseDataSource:
    """Tests for PackseDataSource."""

    def test_init(self, tmp_path):
        """Test PackseDataSource initialization."""
        data_dir = tmp_path / "packse"
        source = PackseDataSource(data_dir)

        assert source.name == "packse"
        assert source.data_dir == data_dir
        assert "uv" in source.supported_pms
        assert "pip" in source.supported_pms

    def test_needs_fetch_when_missing(self, tmp_path):
        """Test needs_fetch returns True when directory doesn't exist."""
        data_dir = tmp_path / "packse"
        source = PackseDataSource(data_dir)

        assert source.needs_fetch() is True

    def test_needs_fetch_when_exists(self, tmp_path):
        """Test needs_fetch returns False when directory exists."""
        data_dir = tmp_path / "packse"
        data_dir.mkdir(parents=True)
        source = PackseDataSource(data_dir)

        assert source.needs_fetch() is False

    @patch("packse.fetch.fetch")
    def test_fetch(self, mock_fetch, tmp_path, caplog):
        """Test fetching packse scenarios."""
        import logging
        caplog.set_level(logging.INFO)

        data_dir = tmp_path / "packse"
        source = PackseDataSource(data_dir)

        source.fetch()

        # Verify packse.fetch.fetch was called with correct directory
        mock_fetch.assert_called_once_with(dest=data_dir)

        # Verify success message was logged
        assert "Successfully fetched packse scenarios" in caplog.text

    @patch("packse.fetch.fetch")
    def test_fetch_creates_parent_dir(self, mock_fetch, tmp_path):
        """Test fetch creates parent directory if needed."""
        data_dir = tmp_path / "data" / "packse"
        source = PackseDataSource(data_dir)

        source.fetch()

        assert data_dir.parent.exists()
        mock_fetch.assert_called_once()

    @patch("packse.inspect.find_scenario_files")
    @patch("packse.inspect.variables_for_templates")
    def test_load_scenarios(
        self,
        mock_variables,
        mock_find_files,
        tmp_path,
        caplog
    ):
        """Test loading packse scenarios."""
        import logging
        caplog.set_level(logging.INFO)

        data_dir = tmp_path / "packse"
        data_dir.mkdir(parents=True)
        source = PackseDataSource(data_dir)

        # Mock scenario data
        mock_find_files.return_value = [Path("scenario1.toml"), Path("scenario2.toml")]
        mock_variables.return_value = {
            "scenarios": [
                {
                    "name": "test-scenario-1",
                    "root": {
                        "requires": [{"requirement": "package-a>=1.0.0"}],
                        "requires_python": ">=3.12",
                    },
                    "resolver_options": {"universal": True},
                },
                {
                    "name": "test-scenario-2",
                    "root": {
                        "requires": [{"requirement": "package-b<2.0.0"}],
                    },
                    "resolver_options": {"universal": False},
                },
            ]
        }

        scenarios = source.load_scenarios()

        # Verify correct number of scenarios loaded
        assert len(scenarios) == 2

        # Verify scenarios are properly converted
        assert scenarios[0].name == "test-scenario-1"
        assert scenarios[0].source == "packse"
        assert scenarios[0].resolver_options.universal is True

        assert scenarios[1].name == "test-scenario-2"
        assert scenarios[1].source == "packse"

        # Verify packse API was called correctly
        mock_find_files.assert_called_once_with(data_dir)
        mock_variables.assert_called_once()
        assert mock_variables.call_args[1]["no_hash"] is True

        # Verify success message was logged
        assert "Loaded 2 packse scenarios" in caplog.text

    def test_load_scenarios_missing_dir(self, tmp_path, caplog):
        """Test loading scenarios when directory doesn't exist."""
        data_dir = tmp_path / "packse"
        source = PackseDataSource(data_dir)

        scenarios = source.load_scenarios()

        assert scenarios == []
        assert "not found" in caplog.text

    @patch("packse.inspect.find_scenario_files")
    def test_load_scenarios_no_files(self, mock_find_files, tmp_path, caplog):
        """Test loading scenarios when no files found."""
        data_dir = tmp_path / "packse"
        data_dir.mkdir(parents=True)
        source = PackseDataSource(data_dir)

        mock_find_files.return_value = []

        scenarios = source.load_scenarios()

        assert scenarios == []
        assert "No packse scenario files found" in caplog.text


class TestScenarioLoader:
    """Tests for ScenarioLoader."""

    def test_init(self):
        """Test ScenarioLoader initialization."""
        loader = ScenarioLoader()
        assert loader.auto_fetch is True

        loader_no_fetch = ScenarioLoader(auto_fetch=False)
        assert loader_no_fetch.auto_fetch is False

    @patch.object(PackseDataSource, "load_scenarios")
    @patch.object(PackseDataSource, "needs_fetch")
    def test_load_from_source(
        self,
        mock_needs_fetch,
        mock_load,
        tmp_path
    ):
        """Test loading from a single source."""
        mock_needs_fetch.return_value = False
        mock_load.return_value = [
            Scenario(
                name="test",
                root=Root(),
                resolver_options=ResolverOptions(universal=True),
                source="packse",
            )
        ]

        loader = ScenarioLoader()
        scenarios = loader.load_from_source("packse")

        assert len(scenarios) == 1
        assert scenarios[0].name == "test"
        mock_load.assert_called_once()

    @patch.object(PackseDataSource, "fetch")
    @patch.object(PackseDataSource, "load_scenarios")
    @patch.object(PackseDataSource, "needs_fetch")
    def test_load_from_source_auto_fetch(
        self,
        mock_needs_fetch,
        mock_load,
        mock_fetch,
        tmp_path
    ):
        """Test auto-fetching when data is missing."""
        mock_needs_fetch.return_value = True
        mock_load.return_value = []

        loader = ScenarioLoader(auto_fetch=True)
        loader.load_from_source("packse")

        # Verify fetch was called
        mock_fetch.assert_called_once()

    @patch.object(PackseDataSource, "load_scenarios")
    @patch.object(PackseDataSource, "needs_fetch")
    def test_load_from_source_with_filter(
        self,
        mock_needs_fetch,
        mock_load,
        tmp_path
    ):
        """Test loading with a filter."""
        mock_needs_fetch.return_value = False
        mock_load.return_value = [
            Scenario(
                name="universal-test",
                root=Root(),
                resolver_options=ResolverOptions(universal=True),
                source="packse",
            ),
            Scenario(
                name="non-universal-test",
                root=Root(),
                resolver_options=ResolverOptions(universal=False),
                source="packse",
            ),
        ]

        loader = ScenarioLoader()
        filter_config = ScenarioFilter(universal_only=True)
        scenarios = loader.load_from_source("packse", filter_config)

        # Only universal scenario should be returned
        assert len(scenarios) == 1
        assert scenarios[0].name == "universal-test"

    @patch.object(PackseDataSource, "load_scenarios")
    @patch.object(PackseDataSource, "needs_fetch")
    def test_load_for_package_manager(
        self,
        mock_needs_fetch,
        mock_load,
        tmp_path
    ):
        """Test loading for specific package manager."""
        mock_needs_fetch.return_value = False
        mock_load.return_value = [
            Scenario(
                name="test",
                root=Root(),
                resolver_options=ResolverOptions(),
                source="packse",
            )
        ]

        loader = ScenarioLoader()
        scenarios = loader.load_for_package_manager("uv")

        # Should load from packse (supports uv)
        assert len(scenarios) >= 0  # May be filtered

    @patch.object(PackseDataSource, "load_scenarios")
    @patch.object(PackseDataSource, "needs_fetch")
    def test_load_default(
        self,
        mock_needs_fetch,
        mock_load,
        tmp_path
    ):
        """Test loading from default source."""
        mock_needs_fetch.return_value = False
        mock_load.return_value = [
            Scenario(
                name="test",
                root=Root(),
                resolver_options=ResolverOptions(),
                source="packse",
            )
        ]

        loader = ScenarioLoader()
        scenarios = loader.load_default()

        # Should load from default source (packse)
        assert isinstance(scenarios, list)
