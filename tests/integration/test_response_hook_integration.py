"""Integration tests for handle_sca_tool_response hook."""

import json
import tempfile
from pathlib import Path

import pytest

from bom_bench import hookimpl
from bom_bench.models.fixture import Fixture, FixtureFiles, FixtureSetEnvironment
from bom_bench.models.sandbox import SandboxConfig
from bom_bench.plugins import pm, reset_plugins
from bom_bench.sandbox.mise import ToolSpec
from bom_bench.sandbox.sandbox import Sandbox
from bom_bench.sca_tools import get_tool_plugin


class MockSCAToolPlugin:
    """Mock SCA tool plugin that implements handle_sca_tool_response."""

    @hookimpl
    def register_sca_tools(self) -> dict:
        return {
            "name": "mock-tool",
            "description": "Mock SCA tool for testing",
            "supported_ecosystems": ["python"],
            "tools": [],
            "command": "echo",
            "args": ["package1==1.0.0", "package2==2.0.0"],
            "env": {},
        }

    @hookimpl
    def handle_sca_tool_response(self, bom_bench, stdout, stderr, output_file_contents):
        """Parse mock tool output and generate CycloneDX SBOM."""
        # Parse packages from stdout (format: package==version)
        packages = []
        # Split by whitespace and newlines to handle all formats
        for token in stdout.strip().split():
            if "==" in token:
                name, version = token.split("==", 1)
                packages.append({"name": name, "version": version})

        # Generate CycloneDX SBOM using bom_bench helper
        sbom = bom_bench.generate_cyclonedx_sbom("test-project", packages)
        return json.dumps(sbom, indent=2)


@pytest.fixture(scope="module")
def mock_plugin():
    """Register mock plugin for testing."""
    reset_plugins()

    # Register mock plugin
    plugin = MockSCAToolPlugin()
    pm.register(plugin, name="test_mock_plugin")

    # Re-initialize plugin system
    from bom_bench.plugins import initialize_plugins

    initialize_plugins()

    yield plugin

    # Cleanup
    pm.unregister(plugin)
    reset_plugins()


class TestResponseHookIntegration:
    """Integration tests for handle_sca_tool_response hook."""

    @pytest.fixture
    def fixture_env(self):
        return FixtureSetEnvironment(
            tools=[ToolSpec(name="python", version="3.12")],
            env={},
            registry_url="",
        )

    @pytest.fixture
    def fixture(self, tmp_path: Path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        manifest = project_dir / "pyproject.toml"
        manifest.write_text('[project]\nname = "test"\n')

        files = FixtureFiles(
            manifest=manifest,
            lock_file=None,
            expected_sbom=None,
            meta=None,
        )

        return Fixture(
            name="test-fixture",
            files=files,
            satisfiable=True,
            description="A test fixture",
        )

    def test_mock_tool_registered(self, mock_plugin):
        """Test that mock tool is registered."""
        from bom_bench.sca_tools import get_tool_info

        tool_info = get_tool_info("mock-tool")
        assert tool_info is not None
        assert tool_info.name == "mock-tool"

    def test_mock_tool_has_plugin(self, mock_plugin):
        """Test that mock tool has associated plugin."""
        plugin = get_tool_plugin("mock-tool")
        assert plugin is not None
        assert hasattr(plugin, "handle_sca_tool_response")

    def test_end_to_end_hook_execution(self, mock_plugin, fixture, fixture_env):
        """Test end-to-end execution with response hook."""
        from bom_bench.sca_tools import get_tool_config

        # Get tool config
        tool_config = get_tool_config("mock-tool")
        assert tool_config is not None

        # Create sandbox and run
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            config = SandboxConfig(
                output_dir=output_dir,
                keep_on_success=True,
                keep_on_failure=True,
            )

            with Sandbox(fixture, fixture_env, tool_config, config) as sandbox:
                result = sandbox.run()

            # Check result
            assert result.success is True
            assert result.actual_sbom_path is not None
            assert result.actual_sbom_path.exists()

            # Read and verify SBOM
            sbom_content = result.actual_sbom_path.read_text()
            sbom = json.loads(sbom_content)

            # Verify SBOM structure
            assert sbom["bomFormat"] == "CycloneDX"
            assert sbom["specVersion"] == "1.6"

            # Verify components were extracted from stdout
            components = sbom.get("components", [])
            assert len(components) == 2

            # Find packages by name
            package_names = [c["name"] for c in components]
            assert "package1" in package_names
            assert "package2" in package_names

            # Verify versions
            for component in components:
                if component["name"] == "package1":
                    assert component["version"] == "1.0.0"
                elif component["name"] == "package2":
                    assert component["version"] == "2.0.0"

    def test_hook_without_output_file(self, mock_plugin, fixture, fixture_env):
        """Test hook works when tool doesn't create output file."""
        from bom_bench.sca_tools import get_tool_config

        tool_config = get_tool_config("mock-tool")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            config = SandboxConfig(
                output_dir=output_dir,
                keep_on_success=True,
            )

            with Sandbox(fixture, fixture_env, tool_config, config) as sandbox:
                result = sandbox.run()

            # Hook should have created the SBOM file
            assert result.success is True
            assert result.actual_sbom_path is not None
            assert result.actual_sbom_path.exists()

            # Verify SBOM was generated by hook
            sbom = json.loads(result.actual_sbom_path.read_text())
            assert "bomFormat" in sbom
