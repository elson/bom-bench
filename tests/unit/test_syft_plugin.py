"""Tests for Syft plugin."""

from bom_bench.sca_tools.syft import register_sca_tools


class TestSyftToolRegistration:
    """Tests for Syft tool registration."""

    def test_syft_registers_correctly(self):
        """Test that Syft registers with correct info."""
        tool = register_sca_tools()

        assert tool["name"] == "syft"
        assert tool["homepage"] == "https://github.com/anchore/syft"

    def test_syft_supported_ecosystems(self):
        """Test Syft supported ecosystems."""
        tool = register_sca_tools()

        ecosystems = tool["supported_ecosystems"]
        assert "python" in ecosystems
        assert "javascript" in ecosystems
        assert "java" in ecosystems
        assert "go" in ecosystems
        assert "rust" in ecosystems
        assert "ruby" in ecosystems
        assert "php" in ecosystems
        assert "dotnet" in ecosystems

    def test_syft_has_declarative_config(self):
        """Test that tool has declarative config for sandbox execution."""
        tool = register_sca_tools()

        assert "tools" in tool
        assert tool["tools"] == [{"name": "syft", "version": "latest"}]
        assert "command" in tool
        assert "args" in tool
        assert "${PROJECT_DIR}" in tool["args"]
        assert any("${OUTPUT_PATH}" in arg for arg in tool["args"])
