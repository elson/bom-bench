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
from bom_bench.sandbox.mise import ToolSpec
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
