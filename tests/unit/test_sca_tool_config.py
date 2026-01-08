"""Tests for SCA tool declarative configuration."""

from bom_bench.models.sca_tool import SCAToolConfig
from bom_bench.sandbox.mise import ToolSpec


class TestSCAToolConfig:
    def test_create_from_dict_new_format(self):
        """Test creating config from new format with command + args + env."""
        data = {
            "name": "snyk",
            "tools": [{"name": "npm:snyk", "version": "latest"}],
            "command": "snyk",
            "args": ["test", "${project_dir}", "--print-deps", ">", "${output_path}"],
            "env": {"SNYK_TOKEN": "${SNYK_TOKEN}"},
            "supported_ecosystems": ["python", "javascript"],
            "description": "Snyk scanner",
        }

        config = SCAToolConfig.from_dict(data)

        assert config.name == "snyk"
        assert len(config.tools) == 1
        assert config.tools[0].name == "npm:snyk"
        assert config.tools[0].version == "latest"
        assert config.command == "snyk"
        assert config.args == ["test", "${project_dir}", "--print-deps", ">", "${output_path}"]
        assert config.env == {"SNYK_TOKEN": "${SNYK_TOKEN}"}
        assert config.supported_ecosystems == ["python", "javascript"]
        assert config.description == "Snyk scanner"

    def test_create_minimal(self):
        """Test creating minimal config with just name and command."""
        data = {
            "name": "test-tool",
            "tools": [],
            "command": "test-tool",
        }

        config = SCAToolConfig.from_dict(data)

        assert config.name == "test-tool"
        assert config.tools == []
        assert config.command == "test-tool"
        assert config.args == []
        assert config.env == {}
        assert config.supported_ecosystems == []
        assert config.description is None

    def test_format_command_new_format(self):
        """Test format_command with new args format."""
        config = SCAToolConfig(
            name="cdxgen",
            tools=[ToolSpec(name="node", version="22")],
            command="cdxgen",
            args=["-o", "${output_path}", "${project_dir}"],
        )

        formatted = config.format_command(
            output_path="/tmp/sbom.json",
            project_dir="/project",
        )

        assert formatted == "cdxgen -o /tmp/sbom.json /project"

    def test_format_command_empty_args(self):
        """Test format_command with empty args."""
        config = SCAToolConfig(
            name="simple-tool",
            tools=[],
            command="scan-all",
            args=[],
        )

        formatted = config.format_command(
            output_path="/tmp/out.json",
            project_dir="/proj",
        )

        assert formatted == "scan-all"

    def test_format_command_with_complex_args(self):
        """Test format_command with redirect and multiple placeholders."""
        config = SCAToolConfig(
            name="snyk",
            tools=[],
            command="snyk",
            args=["test", "${project_dir}", "--json", ">", "${output_path}"],
        )

        formatted = config.format_command(
            output_path="/out/sbom.json",
            project_dir="/my/project",
        )

        assert formatted == "snyk test /my/project --json > /out/sbom.json"


class TestCdxgenPluginConfig:
    def test_cdxgen_returns_declarative_config(self):
        from bom_bench.sca_tools.cdxgen import register_sca_tools

        result = register_sca_tools()

        assert result["name"] == "cdxgen"
        assert "tools" in result
        assert any(t["name"] == "npm:@cyclonedx/cdxgen" for t in result["tools"])
        assert "command" in result
        assert "args" in result
        assert "${output_path}" in result["args"]
        assert "${project_dir}" in result["args"]


class TestSyftPluginConfig:
    def test_syft_returns_declarative_config(self):
        from bom_bench.sca_tools.syft import register_sca_tools

        result = register_sca_tools()

        assert result["name"] == "syft"
        assert "tools" in result
        assert any(t["name"] == "syft" for t in result["tools"])
        assert "command" in result
        assert "args" in result
        assert any("${output_path}" in arg for arg in result["args"])
        assert "${project_dir}" in result["args"]


class TestGetToolConfig:
    def test_get_tool_config_cdxgen(self):
        from bom_bench.sca_tools import get_tool_config

        config = get_tool_config("cdxgen")

        assert config is not None
        assert config.name == "cdxgen"
        assert len(config.tools) >= 1
        assert config.tools[0].name == "npm:@cyclonedx/cdxgen"
        assert "${output_path}" in config.args
        assert "${project_dir}" in config.args

    def test_get_tool_config_syft(self):
        from bom_bench.sca_tools import get_tool_config

        config = get_tool_config("syft")

        assert config is not None
        assert config.name == "syft"
        assert len(config.tools) >= 1
        assert any("${output_path}" in arg for arg in config.args)
        assert "${project_dir}" in config.args

    def test_get_tool_config_not_found(self):
        from bom_bench.sca_tools import get_tool_config

        config = get_tool_config("nonexistent-tool")

        assert config is None
