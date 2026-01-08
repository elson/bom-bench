import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from bom_bench.models.fixture import (
    Fixture,
    FixtureFiles,
    FixtureSetEnvironment,
)
from bom_bench.models.sandbox import SandboxConfig, SandboxResult
from bom_bench.sandbox.mise import MiseRunResult, ToolSpec
from bom_bench.sandbox.sandbox import Sandbox, SCAToolConfig


class TestSCAToolConfig:
    def test_create_config(self):
        config = SCAToolConfig(
            name="cdxgen",
            tools=[ToolSpec(name="node", version="22")],
            command="cdxgen",
            args=["-o", "${OUTPUT_PATH}", "${PROJECT_DIR}"],
            env={},
            supported_ecosystems=["python", "javascript"],
        )
        assert config.name == "cdxgen"
        assert config.command == "cdxgen"
        assert config.args == ["-o", "${OUTPUT_PATH}", "${PROJECT_DIR}"]
        assert len(config.tools) == 1

    def test_config_from_dict(self):
        data = {
            "name": "syft",
            "tools": [{"name": "syft", "version": "1.0.0"}],
            "command": "syft",
            "args": ["${PROJECT_DIR}", "-o", "cyclonedx-json=${OUTPUT_PATH}"],
            "env": {"SYFT_CHECK_FOR_APP_UPDATE": "false"},
            "supported_ecosystems": ["python"],
        }

        config = SCAToolConfig.from_dict(data)

        assert config.name == "syft"
        assert len(config.tools) == 1
        assert config.env["SYFT_CHECK_FOR_APP_UPDATE"] == "false"


class TestSandbox:
    @pytest.fixture
    def fixture_env(self):
        return FixtureSetEnvironment(
            tools=[
                ToolSpec(name="uv", version="0.5.11"),
                ToolSpec(name="python", version="3.12"),
            ],
            env={"UV_INDEX_URL": "http://localhost:3141/simple"},
            registry_url="http://localhost:3141/simple-html",
        )

    @pytest.fixture
    def fixture(self, tmp_path: Path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        manifest = project_dir / "pyproject.toml"
        manifest.write_text('[project]\nname = "test"\n')

        lock_file = project_dir / "uv.lock"
        lock_file.write_text("# lock file content\n")

        expected_sbom = project_dir / "expected.cdx.json"
        expected_sbom.write_text('{"bomFormat": "CycloneDX"}')

        meta = project_dir / "meta.json"
        meta.write_text('{"satisfiable": true}')

        files = FixtureFiles(
            manifest=manifest,
            lock_file=lock_file,
            expected_sbom=expected_sbom,
            meta=meta,
        )

        return Fixture(
            name="test-fixture",
            files=files,
            satisfiable=True,
            description="A test fixture",
        )

    @pytest.fixture
    def sca_tool(self):
        return SCAToolConfig(
            name="cdxgen",
            tools=[ToolSpec(name="node", version="22")],
            command="echo",
            args=["mock sbom", ">", "${OUTPUT_PATH}"],
            env={},
            supported_ecosystems=["python"],
        )

    def test_sandbox_creates_temp_dir(self, fixture, fixture_env, sca_tool):
        with Sandbox(fixture, fixture_env, sca_tool) as sandbox:
            assert sandbox.sandbox_dir is not None
            assert sandbox.sandbox_dir.exists()
            assert sandbox.sandbox_dir.is_dir()

    def test_sandbox_cleans_up_on_exit(self, fixture, fixture_env, sca_tool):
        config = SandboxConfig(keep_on_success=False, keep_on_failure=False)

        with Sandbox(fixture, fixture_env, sca_tool, config) as sandbox:
            sandbox_dir = sandbox.sandbox_dir

        assert not sandbox_dir.exists()

    def test_sandbox_keeps_on_failure(self, fixture, fixture_env, sca_tool):
        config = SandboxConfig(keep_on_failure=True)

        try:
            with Sandbox(fixture, fixture_env, sca_tool, config) as sandbox:
                sandbox_dir = sandbox.sandbox_dir
                raise RuntimeError("Simulated failure")
        except RuntimeError:
            pass

        assert sandbox_dir.exists()
        shutil.rmtree(sandbox_dir)

    def test_sandbox_copies_fixture_files(self, fixture, fixture_env, sca_tool):
        with Sandbox(fixture, fixture_env, sca_tool) as sandbox:
            project_dir = sandbox.sandbox_dir / "project"
            assert project_dir.exists()
            assert (project_dir / "pyproject.toml").exists()
            assert (project_dir / "uv.lock").exists()

    def test_sandbox_generates_mise_toml(self, fixture, fixture_env, sca_tool):
        with Sandbox(fixture, fixture_env, sca_tool) as sandbox:
            mise_toml = sandbox.sandbox_dir / "mise.toml"
            assert mise_toml.exists()

            content = mise_toml.read_text()
            assert "[tools]" in content
            assert 'uv = "0.5.11"' in content
            assert 'node = "22"' in content
            assert "[tasks.sca]" in content

    def test_sandbox_uses_custom_temp_dir(self, fixture, fixture_env, sca_tool, tmp_path: Path):
        custom_dir = tmp_path / "my-sandbox"
        config = SandboxConfig(temp_dir=custom_dir, keep_on_success=True)

        with Sandbox(fixture, fixture_env, sca_tool, config) as sandbox:
            assert sandbox.sandbox_dir == custom_dir
            assert custom_dir.exists()

    def test_sandbox_run_returns_result(self, fixture, fixture_env, sca_tool):
        with (
            Sandbox(fixture, fixture_env, sca_tool) as sandbox,
            patch.object(sandbox, "_execute_sca_tool") as mock_execute,
        ):
            mock_execute.return_value = SandboxResult(
                fixture_name="test-fixture",
                tool_name="cdxgen",
                success=True,
                actual_sbom_path=sandbox.sandbox_dir / "actual.cdx.json",
                duration_seconds=1.0,
                exit_code=0,
                stdout="Success",
                stderr="",
            )

            result = sandbox.run()

            assert result.success is True
            assert result.fixture_name == "test-fixture"
            assert result.tool_name == "cdxgen"

    def test_sandbox_output_path(self, fixture, fixture_env, sca_tool):
        with Sandbox(fixture, fixture_env, sca_tool) as sandbox:
            assert sandbox.output_path == sandbox.sandbox_dir / "actual.cdx.json"

    def test_sandbox_project_dir(self, fixture, fixture_env, sca_tool):
        with Sandbox(fixture, fixture_env, sca_tool) as sandbox:
            assert sandbox.project_dir == sandbox.sandbox_dir / "project"


class TestSandboxHookInvocation:
    """Tests for _handle_tool_response hook invocation."""

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

    @pytest.fixture
    def sca_tool(self):
        return SCAToolConfig(
            name="test-tool",
            tools=[],
            command="echo",
            args=["test"],
            env={},
            supported_ecosystems=["python"],
        )

    def test_handle_tool_response_no_plugin(self, fixture, fixture_env, sca_tool):
        """Test _handle_tool_response when no plugin is found."""
        with Sandbox(fixture, fixture_env, sca_tool) as sandbox:
            mise_result = MiseRunResult(
                success=True,
                exit_code=0,
                stdout="output",
                stderr="",
                duration_seconds=1.0,
            )

            # Should not raise error when plugin doesn't exist
            sandbox._handle_tool_response(mise_result)

    def test_handle_tool_response_plugin_no_hook(self, fixture, fixture_env, sca_tool):
        """Test _handle_tool_response when plugin doesn't implement hook."""
        # Use cdxgen which exists but doesn't implement handle_sca_tool_response
        sca_tool.name = "cdxgen"

        with Sandbox(fixture, fixture_env, sca_tool) as sandbox:
            mise_result = MiseRunResult(
                success=True,
                exit_code=0,
                stdout="output",
                stderr="",
                duration_seconds=1.0,
            )

            # Should not raise error when plugin doesn't implement hook
            sandbox._handle_tool_response(mise_result)

    def test_handle_tool_response_hook_called(self, fixture, fixture_env, sca_tool):
        """Test _handle_tool_response calls hook and writes result."""
        with Sandbox(fixture, fixture_env, sca_tool) as sandbox:
            # Create a mock plugin with handle_sca_tool_response
            class MockPlugin:
                def handle_sca_tool_response(self, bom_bench, stdout, stderr, output_file_contents):
                    # Generate mock SBOM
                    sbom = {"bomFormat": "CycloneDX", "specVersion": "1.6"}
                    return json.dumps(sbom, indent=2)

            mock_plugin = MockPlugin()

            # Mock get_tool_plugin to return our mock
            with patch("bom_bench.sca_tools.get_tool_plugin", return_value=mock_plugin):
                mise_result = MiseRunResult(
                    success=True,
                    exit_code=0,
                    stdout="package1==1.0.0\npackage2==2.0.0",
                    stderr="",
                    duration_seconds=1.0,
                )

                sandbox._handle_tool_response(mise_result)

                # Check that SBOM was written
                assert sandbox.output_path.exists()
                content = sandbox.output_path.read_text()
                sbom = json.loads(content)
                assert sbom["bomFormat"] == "CycloneDX"
                assert sbom["specVersion"] == "1.6"

    def test_handle_tool_response_hook_returns_none(self, fixture, fixture_env, sca_tool):
        """Test _handle_tool_response when hook returns None."""
        with Sandbox(fixture, fixture_env, sca_tool) as sandbox:
            # Create a mock plugin that returns None
            class MockPlugin:
                def handle_sca_tool_response(self, bom_bench, stdout, stderr, output_file_contents):
                    return None  # Use default behavior

            mock_plugin = MockPlugin()

            # Pre-create output file
            sandbox.output_path.write_text("original content")

            with patch("bom_bench.sca_tools.get_tool_plugin", return_value=mock_plugin):
                mise_result = MiseRunResult(
                    success=True,
                    exit_code=0,
                    stdout="output",
                    stderr="",
                    duration_seconds=1.0,
                )

                sandbox._handle_tool_response(mise_result)

                # Original content should be unchanged
                assert sandbox.output_path.read_text() == "original content"

    def test_handle_tool_response_receives_correct_args(self, fixture, fixture_env, sca_tool):
        """Test _handle_tool_response passes correct arguments to hook."""
        with Sandbox(fixture, fixture_env, sca_tool) as sandbox:
            # Pre-create output file
            sandbox.output_path.write_text("existing output")

            received_args = {}

            class MockPlugin:
                def handle_sca_tool_response(self, bom_bench, stdout, stderr, output_file_contents):
                    received_args["bom_bench"] = bom_bench
                    received_args["stdout"] = stdout
                    received_args["stderr"] = stderr
                    received_args["output_file_contents"] = output_file_contents
                    return None

            mock_plugin = MockPlugin()

            with patch("bom_bench.sca_tools.get_tool_plugin", return_value=mock_plugin):
                mise_result = MiseRunResult(
                    success=True,
                    exit_code=0,
                    stdout="test stdout",
                    stderr="test stderr",
                    duration_seconds=1.0,
                )

                sandbox._handle_tool_response(mise_result)

                # Verify correct arguments were passed
                assert received_args["stdout"] == "test stdout"
                assert received_args["stderr"] == "test stderr"
                assert received_args["output_file_contents"] == "existing output"
                # Check bom_bench module has generate_cyclonedx_sbom
                assert hasattr(received_args["bom_bench"], "generate_cyclonedx_sbom")
