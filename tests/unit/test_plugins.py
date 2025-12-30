"""Tests for plugin system."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from bom_bench.models.sca_tool import ScanStatus, SCAToolInfo
from bom_bench.plugins import (
    get_plugins,
    initialize_plugins,
    reset_plugins,
)
from bom_bench.sca_tools import (
    check_tool_available,
    get_registered_tools,
    get_tool_info,
    list_available_tools,
    scan_project,
)


class TestPluginInitialization:
    """Tests for plugin initialization."""

    def setup_method(self):
        """Reset plugins before each test."""
        reset_plugins()

    def test_initialize_plugins(self):
        """Test plugin initialization."""
        initialize_plugins()

        tools = get_registered_tools()
        assert "cdxgen" in tools

    def test_initialize_plugins_idempotent(self):
        """Test that initialize_plugins is idempotent."""
        initialize_plugins()
        tools1 = get_registered_tools()

        initialize_plugins()
        tools2 = get_registered_tools()

        assert tools1 == tools2

    def test_reset_plugins(self):
        """Test plugin reset."""
        initialize_plugins()
        assert len(get_registered_tools()) > 0

        reset_plugins()
        # After reset, next call should re-initialize
        tools = get_registered_tools()
        assert "cdxgen" in tools


class TestToolRegistry:
    """Tests for tool registry functions."""

    def setup_method(self):
        """Reset and initialize plugins."""
        reset_plugins()
        initialize_plugins()

    def test_get_registered_tools(self):
        """Test getting registered tools."""
        tools = get_registered_tools()

        assert isinstance(tools, dict)
        assert "cdxgen" in tools
        assert isinstance(tools["cdxgen"], SCAToolInfo)

    def test_list_available_tools(self):
        """Test listing available tools."""
        tools = list_available_tools()

        assert isinstance(tools, list)
        assert "cdxgen" in tools

    def test_get_tool_info_exists(self):
        """Test getting info for existing tool."""
        info = get_tool_info("cdxgen")

        assert info is not None
        assert info.name == "cdxgen"
        assert "python" in info.supported_ecosystems

    def test_get_tool_info_not_exists(self):
        """Test getting info for non-existent tool."""
        info = get_tool_info("nonexistent")

        assert info is None


class TestToolAvailability:
    """Tests for tool availability checking."""

    def setup_method(self):
        """Reset and initialize plugins."""
        reset_plugins()
        initialize_plugins()

    def test_check_tool_available_not_registered(self):
        """Test checking availability for unregistered tool."""
        available = check_tool_available("nonexistent")
        assert available is False

    @patch("shutil.which")
    def test_check_cdxgen_available(self, mock_which):
        """Test checking cdxgen availability when installed."""
        mock_which.return_value = "/usr/local/bin/cdxgen"
        reset_plugins()
        initialize_plugins()

        available = check_tool_available("cdxgen")
        assert available is True

    @patch("shutil.which")
    def test_check_cdxgen_not_available(self, mock_which):
        """Test checking cdxgen availability when not installed."""
        mock_which.return_value = None
        reset_plugins()
        initialize_plugins()

        available = check_tool_available("cdxgen")
        assert available is False


class TestSBOMGeneration:
    """Tests for SBOM generation via plugins."""

    def setup_method(self):
        """Reset and initialize plugins."""
        reset_plugins()
        initialize_plugins()

    def test_generate_sbom_unregistered_tool(self):
        """Test SBOM generation with unregistered tool."""
        result = scan_project(
            tool_name="nonexistent",
            project_dir=Path("/project"),
            output_path=Path("/output.json"),
            ecosystem="python",
        )

        assert result is None

    @patch("subprocess.run")
    def test_generate_sbom_cdxgen_success(self, mock_run, tmp_path):
        """Test successful cdxgen SBOM generation."""
        # Create a mock output file
        output_path = tmp_path / "sbom.json"
        output_path.write_text('{"bomFormat": "CycloneDX"}')

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = scan_project(
            tool_name="cdxgen", project_dir=tmp_path, output_path=output_path, ecosystem="python"
        )

        assert result is not None
        assert result.status == ScanStatus.SUCCESS
        assert result.sbom_path == output_path

    @patch("subprocess.run")
    def test_generate_sbom_cdxgen_failure(self, mock_run, tmp_path):
        """Test cdxgen SBOM generation failure."""
        output_path = tmp_path / "sbom.json"

        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Error: something went wrong"
        )

        result = scan_project(
            tool_name="cdxgen", project_dir=tmp_path, output_path=output_path, ecosystem="python"
        )

        assert result is not None
        assert result.status == ScanStatus.TOOL_FAILED
        assert "Error" in result.error_message


class TestPluginInfo:
    """Tests for plugin information."""

    def setup_method(self):
        """Reset and initialize plugins."""
        reset_plugins()
        initialize_plugins()

    def test_get_plugins(self):
        """Test getting plugin info."""
        plugins = get_plugins()

        assert isinstance(plugins, list)
        assert len(plugins) >= 1

        # Find cdxgen plugin
        cdxgen_plugin = None
        for p in plugins:
            if "cdxgen" in p.get("name", ""):
                cdxgen_plugin = p
                break

        assert cdxgen_plugin is not None


class TestCdxgenPlugin:
    """Tests specific to the bundled cdxgen plugin."""

    def setup_method(self):
        """Reset and initialize plugins."""
        reset_plugins()
        initialize_plugins()

    def test_cdxgen_tool_info(self):
        """Test cdxgen tool info."""
        info = get_tool_info("cdxgen")

        assert info.name == "cdxgen"
        assert info.description is not None
        assert "python" in info.supported_ecosystems
        assert info.homepage == "https://github.com/CycloneDX/cdxgen"

    @patch("shutil.which")
    def test_cdxgen_availability_check(self, mock_which):
        """Test cdxgen availability check."""
        # When cdxgen is installed
        mock_which.return_value = "/usr/local/bin/cdxgen"
        reset_plugins()
        assert check_tool_available("cdxgen") is True

        # When cdxgen is not installed
        mock_which.return_value = None
        reset_plugins()
        assert check_tool_available("cdxgen") is False
