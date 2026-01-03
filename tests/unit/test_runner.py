"""Tests for the new sandbox-based benchmark runner."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bom_bench.models.fixture import Fixture, FixtureFiles, FixtureSet, FixtureSetEnvironment
from bom_bench.models.sandbox import SandboxResult
from bom_bench.models.sca_tool import SCAToolConfig
from bom_bench.sandbox.mise import ToolSpec


class TestFixtureExecutor:
    @pytest.fixture
    def sample_fixture(self, tmp_path: Path):
        """Create a sample fixture with files."""
        manifest_path = tmp_path / "pyproject.toml"
        manifest_path.write_text('[project]\nname = "test"')

        meta_path = tmp_path / "meta.json"
        meta_path.write_text('{"satisfiable": true}')

        expected_path = tmp_path / "expected.cdx.json"
        expected_sbom = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "components": [
                {"name": "requests", "version": "2.31.0", "purl": "pkg:pypi/requests@2.31.0"}
            ],
        }
        expected_path.write_text(json.dumps(expected_sbom))

        return Fixture(
            name="test-fixture",
            files=FixtureFiles(
                manifest=manifest_path,
                lock_file=None,
                expected_sbom=expected_path,
                meta=meta_path,
            ),
            satisfiable=True,
            description="Test fixture",
        )

    @pytest.fixture
    def sample_fixture_set(self, sample_fixture):
        """Create a sample fixture set."""
        return FixtureSet(
            name="test-set",
            description="Test fixture set",
            ecosystem="python",
            environment=FixtureSetEnvironment(
                tools=[ToolSpec(name="uv", version="0.5.11")],
                env_vars={},
                registry_url="http://localhost:3141/simple",
            ),
            fixtures=[sample_fixture],
        )

    @pytest.fixture
    def sample_tool_config(self):
        """Create a sample SCA tool config."""
        return SCAToolConfig(
            name="test-tool",
            tools=[ToolSpec(name="node", version="22")],
            command="test-tool -o {output_path} {project_dir}",
            supported_ecosystems=["python"],
        )

    def test_execute_fixture_success(
        self, sample_fixture, sample_fixture_set, sample_tool_config, tmp_path: Path
    ):
        from bom_bench.runner.executor import FixtureExecutor

        # Create mock sandbox result with actual SBOM
        mock_result = SandboxResult(
            fixture_name="test-fixture",
            tool_name="test-tool",
            success=True,
            actual_sbom_path=Path("/tmp/actual.cdx.json"),
            duration_seconds=1.5,
        )

        with (
            patch("bom_bench.runner.executor.Sandbox") as mock_sandbox_cls,
            patch("bom_bench.runner.executor.load_actual_sbom") as mock_load_actual,
            patch("bom_bench.runner.executor.load_expected_sbom") as mock_load_expected,
        ):
            # Setup mocks
            mock_sandbox_instance = MagicMock()
            mock_sandbox_instance.__enter__ = MagicMock(return_value=mock_sandbox_instance)
            mock_sandbox_instance.__exit__ = MagicMock(return_value=None)
            mock_sandbox_instance.run.return_value = mock_result
            mock_sandbox_cls.return_value = mock_sandbox_instance

            mock_load_actual.return_value = {
                "components": [
                    {"name": "requests", "version": "2.31.0", "purl": "pkg:pypi/requests@2.31.0"}
                ]
            }
            mock_load_expected.return_value = (
                {
                    "components": [
                        {
                            "name": "requests",
                            "version": "2.31.0",
                            "purl": "pkg:pypi/requests@2.31.0",
                        }
                    ]
                },
                True,
            )

            executor = FixtureExecutor()
            result = executor.execute(
                fixture=sample_fixture,
                fixture_set_env=sample_fixture_set.environment,
                tool_config=sample_tool_config,
                fixture_set_name="test-set",
                output_dir=tmp_path,
            )

            assert result.status.value == "success"
            assert result.metrics is not None
            assert result.metrics.precision == 1.0
            assert result.metrics.recall == 1.0

    def test_execute_fixture_unsatisfiable(
        self, sample_fixture_set, sample_tool_config, tmp_path: Path
    ):
        from bom_bench.runner.executor import FixtureExecutor

        manifest_path = tmp_path / "pyproject.toml"
        manifest_path.write_text('[project]\nname = "test"')
        meta_path = tmp_path / "meta.json"
        meta_path.write_text('{"satisfiable": false}')

        unsatisfiable_fixture = Fixture(
            name="unsatisfiable",
            files=FixtureFiles(
                manifest=manifest_path,
                lock_file=None,
                expected_sbom=None,
                meta=meta_path,
            ),
            satisfiable=False,
        )

        executor = FixtureExecutor()
        result = executor.execute(
            fixture=unsatisfiable_fixture,
            fixture_set_env=sample_fixture_set.environment,
            tool_config=sample_tool_config,
            fixture_set_name="test-set",
            output_dir=tmp_path,
        )

        assert result.status.value == "unsatisfiable"
        assert result.metrics is None


class TestBenchmarkRunner:
    def test_runner_creation(self, tmp_path: Path):
        from bom_bench.runner import BenchmarkRunner

        runner = BenchmarkRunner(output_dir=tmp_path)
        assert runner.output_dir == tmp_path

    def test_runner_run_empty_fixtures(self, tmp_path: Path):
        from bom_bench.runner import BenchmarkRunner

        with patch("bom_bench.runner.runner.FixtureSetLoader") as mock_loader_cls:
            mock_loader = MagicMock()
            mock_loader.load_all.return_value = []
            mock_loader_cls.return_value = mock_loader

            runner = BenchmarkRunner(output_dir=tmp_path)
            results = runner.run(tools=["cdxgen"])

            assert results == []
