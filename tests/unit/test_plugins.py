"""Tests for plugin system."""

from bom_bench.models.sca_tool import SCAToolInfo
from bom_bench.plugins import (
    get_plugins,
    initialize_plugins,
    reset_plugins,
)
from bom_bench.sca_tools import (
    get_registered_tools,
    get_tool_info,
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
