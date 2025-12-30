"""Tests for package manager implementations."""

import tempfile
from pathlib import Path

import pytest

from bom_bench.models.package_manager import ProcessScenarioResult, ProcessStatus
from bom_bench.models.scenario import Requirement, ResolverOptions, Root, Scenario
from bom_bench.package_managers import (
    check_package_manager_available,
    get_package_manager_info,
    list_available_package_managers,
    process_scenario,
)


class TestProcessScenarioHookSignature:
    """Test that process_scenario hook receives correct parameters."""

    def test_hook_receives_bom_bench_module(self):
        """Hook should receive bom_bench module for dependency injection."""
        import bom_bench
        from bom_bench import hookimpl
        from bom_bench.package_managers import _register_package_managers
        from bom_bench.plugins import pm, reset_plugins

        captured_params: dict = {}

        class TestPlugin:
            @hookimpl
            def register_package_managers(self):
                return {
                    "name": "test-pm",
                    "ecosystem": "python",
                    "description": "Test PM",
                    "supported_sources": ["test"],
                    "installed": True,
                }

            @hookimpl
            def process_scenario(self, pm_name, scenario, output_dir, bom_bench, timeout=120):
                if pm_name != "test-pm":
                    return None
                captured_params["bom_bench"] = bom_bench
                captured_params["scenario"] = scenario
                return {
                    "pm_name": "test-pm",
                    "status": "success",
                    "duration_seconds": 0.1,
                    "exit_code": 0,
                }

        reset_plugins()
        from bom_bench.plugins import initialize_plugins

        initialize_plugins()
        pm.register(TestPlugin())
        _register_package_managers(pm)

        scenario = Scenario(
            name="test",
            root=Root(requires=[Requirement(requirement="pkg>=1.0")]),
            resolver_options=ResolverOptions(universal=True),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            process_scenario("test-pm", scenario, Path(tmpdir))

        assert "bom_bench" in captured_params
        assert captured_params["bom_bench"] is bom_bench
        assert hasattr(captured_params["bom_bench"], "generate_sbom_file")
        assert hasattr(captured_params["bom_bench"], "generate_meta_file")
        assert hasattr(captured_params["bom_bench"], "get_logger")

        reset_plugins()

    def test_hook_receives_scenario_as_dict(self):
        """Hook should receive scenario as dict, not typed dataclass."""
        from bom_bench import hookimpl
        from bom_bench.package_managers import _register_package_managers
        from bom_bench.plugins import pm, reset_plugins

        captured_params: dict = {}

        class TestPlugin:
            @hookimpl
            def register_package_managers(self):
                return {
                    "name": "test-pm-dict",
                    "ecosystem": "python",
                    "description": "Test PM",
                    "supported_sources": ["test"],
                    "installed": True,
                }

            @hookimpl
            def process_scenario(self, pm_name, scenario, output_dir, bom_bench, timeout=120):
                if pm_name != "test-pm-dict":
                    return None
                captured_params["scenario"] = scenario
                return {
                    "pm_name": "test-pm-dict",
                    "status": "success",
                    "duration_seconds": 0.1,
                    "exit_code": 0,
                }

        reset_plugins()
        from bom_bench.plugins import initialize_plugins

        initialize_plugins()
        pm.register(TestPlugin())
        _register_package_managers(pm)

        scenario = Scenario(
            name="dict-test",
            root=Root(
                requires=[Requirement(requirement="pkg>=1.0", extras=["dev"])],
                requires_python=">=3.12",
            ),
            resolver_options=ResolverOptions(universal=True),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            process_scenario("test-pm-dict", scenario, Path(tmpdir))

        assert "scenario" in captured_params
        assert isinstance(captured_params["scenario"], dict)
        assert captured_params["scenario"]["name"] == "dict-test"
        assert captured_params["scenario"]["root"]["requires_python"] == ">=3.12"
        assert captured_params["scenario"]["root"]["requires"][0]["requirement"] == "pkg>=1.0"

        reset_plugins()


class TestPackageManagerRegistry:
    """Test package manager registry functions via plugin API."""

    def test_list_available_package_managers(self):
        """Test listing available package managers."""
        pms = list_available_package_managers()
        assert isinstance(pms, list)
        assert "uv" in pms

    def test_check_pm_available_uv(self):
        """Test checking UV package manager availability."""
        # UV should be available (it's in our dev dependencies)
        assert check_package_manager_available("uv") is True

    def test_check_pm_available_invalid(self):
        """Test checking non-existent package manager."""
        assert check_package_manager_available("nonexistent") is False


class TestUVPackageManagerPluginAPI:
    """Test UV package manager via plugin API."""

    @pytest.fixture
    def simple_scenario(self):
        """Create a simple test scenario."""
        return Scenario(
            name="test-scenario",
            root=Root(
                requires=[
                    Requirement(requirement="package-a>=1.0.0"),
                    Requirement(requirement="package-b<2.0.0"),
                ],
                requires_python=">=3.12",
            ),
            resolver_options=ResolverOptions(universal=True, required_environments=[]),
            source="packse",
        )

    @pytest.fixture
    def scenario_with_environments(self):
        """Create a scenario with required environments."""
        return Scenario(
            name="test-universal",
            root=Root(
                requires=[
                    Requirement(requirement="package-x>=1.0.0"),
                ],
                requires_python=">=3.8",
            ),
            resolver_options=ResolverOptions(
                universal=True,
                required_environments=["python_version >= '3.8'", "sys_platform == 'linux'"],
            ),
            source="packse",
        )

    def test_get_pm_info_uv(self):
        """Test getting PM info for UV."""
        pm_info = get_package_manager_info("uv")
        assert pm_info is not None
        assert pm_info.name == "uv"
        assert pm_info.ecosystem == "python"
        assert "packse" in pm_info.supported_sources

    def test_get_pm_info_invalid(self):
        """Test getting PM info for non-existent PM."""
        pm_info = get_package_manager_info("nonexistent")
        assert pm_info is None

    def test_process_scenario_success(self, simple_scenario):
        """Test processing a scenario (will fail/be unsatisfiable without packse server)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # This test will actually try to run uv lock, which will fail/be unsatisfiable
            # without a packse server. We're testing the interface.
            result = process_scenario("uv", simple_scenario, output_dir)

            # Result should be ProcessScenarioResult
            assert result is not None
            assert isinstance(result, ProcessScenarioResult)
            assert result.pm_name == "uv"
            assert result.status in [
                ProcessStatus.SUCCESS,
                ProcessStatus.FAILED,
                ProcessStatus.TIMEOUT,
                ProcessStatus.UNSATISFIABLE,
            ]
            assert result.duration_seconds >= 0

            # Files discovered by convention (no path fields in result)
            manifest_path = output_dir / "assets" / "pyproject.toml"
            assert manifest_path.exists()

            # If successful, check that SBOM was created by convention
            if result.status == ProcessStatus.SUCCESS:
                assert (output_dir / "expected.cdx.json").exists()
                assert (output_dir / "meta.json").exists()

    def test_process_scenario_invalid_pm(self, simple_scenario):
        """Test processing scenario with non-existent PM."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            result = process_scenario("nonexistent", simple_scenario, output_dir)
            assert result is None
