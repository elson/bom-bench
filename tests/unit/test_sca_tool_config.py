"""Tests for SCA tool declarative configuration."""

from bom_bench.models.sca_tool import SCAToolConfig
from bom_bench.sandbox.mise import ToolSpec


class TestSCAToolConfig:
    def test_create_from_dict(self):
        data = {
            "name": "cdxgen",
            "tools": [{"name": "node", "version": "22"}],
            "command": "cdxgen -o {output_path} {project_dir}",
            "env_vars": {"CDXGEN_DEBUG": "true"},
            "supported_ecosystems": ["python", "javascript"],
            "description": "CycloneDX Generator",
        }

        config = SCAToolConfig.from_dict(data)

        assert config.name == "cdxgen"
        assert len(config.tools) == 1
        assert config.tools[0].name == "node"
        assert config.tools[0].version == "22"
        assert config.command == "cdxgen -o {output_path} {project_dir}"
        assert config.env_vars == {"CDXGEN_DEBUG": "true"}
        assert config.supported_ecosystems == ["python", "javascript"]
        assert config.description == "CycloneDX Generator"

    def test_create_minimal(self):
        data = {
            "name": "test-tool",
            "tools": [],
            "command": "test-tool scan",
        }

        config = SCAToolConfig.from_dict(data)

        assert config.name == "test-tool"
        assert config.tools == []
        assert config.command == "test-tool scan"
        assert config.env_vars == {}
        assert config.supported_ecosystems == []
        assert config.description is None

    def test_format_command(self):
        config = SCAToolConfig(
            name="cdxgen",
            tools=[ToolSpec(name="node", version="22")],
            command="cdxgen -o {output_path} {project_dir}",
        )

        formatted = config.format_command(
            output_path="/tmp/sbom.json",
            project_dir="/project",
        )

        assert formatted == "cdxgen -o /tmp/sbom.json /project"


class TestCdxgenPluginConfig:
    def test_cdxgen_returns_declarative_config(self):
        from bom_bench.sca_tools.cdxgen import register_sca_tools

        result = register_sca_tools()

        assert result["name"] == "cdxgen"
        assert "tools" in result
        assert any(t["name"] == "npm:@cyclonedx/cdxgen" for t in result["tools"])
        assert "command" in result
        assert "{output_path}" in result["command"]
        assert "{project_dir}" in result["command"]


class TestSyftPluginConfig:
    def test_syft_returns_declarative_config(self):
        from bom_bench.sca_tools.syft import register_sca_tools

        result = register_sca_tools()

        assert result["name"] == "syft"
        assert "tools" in result
        assert any(t["name"] == "syft" for t in result["tools"])
        assert "command" in result
        assert "{output_path}" in result["command"]
        assert "{project_dir}" in result["command"]


class TestGetToolConfig:
    def test_get_tool_config_cdxgen(self):
        from bom_bench.sca_tools import get_tool_config

        config = get_tool_config("cdxgen")

        assert config is not None
        assert config.name == "cdxgen"
        assert len(config.tools) >= 1
        assert config.tools[0].name == "npm:@cyclonedx/cdxgen"
        assert "{output_path}" in config.command
        assert "{project_dir}" in config.command

    def test_get_tool_config_syft(self):
        from bom_bench.sca_tools import get_tool_config

        config = get_tool_config("syft")

        assert config is not None
        assert config.name == "syft"
        assert len(config.tools) >= 1
        assert "{output_path}" in config.command
        assert "{project_dir}" in config.command

    def test_get_tool_config_not_found(self):
        from bom_bench.sca_tools import get_tool_config

        config = get_tool_config("nonexistent-tool")

        assert config is None
