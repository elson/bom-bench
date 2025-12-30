"""Tests for package manager implementations."""

import tempfile
from pathlib import Path

import pytest

from bom_bench.models.scenario import Scenario, Root, Requirement, ResolverOptions
from bom_bench.models.package_manager import ProcessStatus, ProcessScenarioResult
from bom_bench.plugins import initialize_plugins
from bom_bench.package_managers import (
    package_manager_process_scenario,
    list_available_package_managers,
    check_package_manager_available,
    get_package_manager_info,
)


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
                requires_python=">=3.12"
            ),
            resolver_options=ResolverOptions(
                universal=True,
                required_environments=[]
            ),
            source="packse"
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
                requires_python=">=3.8"
            ),
            resolver_options=ResolverOptions(
                universal=True,
                required_environments=["python_version >= '3.8'", "sys_platform == 'linux'"]
            ),
            source="packse"
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
            result = package_manager_process_scenario("uv", simple_scenario, output_dir)

            # Result should be ProcessScenarioResult
            assert result is not None
            assert isinstance(result, ProcessScenarioResult)
            assert result.pm_name == "uv"
            assert result.status in [ProcessStatus.SUCCESS, ProcessStatus.FAILED, ProcessStatus.TIMEOUT, ProcessStatus.UNSATISFIABLE]
            assert result.duration_seconds >= 0

            # Manifest should always be created
            assert result.manifest_path is not None
            assert result.manifest_path.exists()

            # If successful, check that SBOM was created
            if result.status == ProcessStatus.SUCCESS:
                assert result.sbom_path is not None
                assert result.meta_path is not None

    def test_process_scenario_invalid_pm(self, simple_scenario):
        """Test processing scenario with non-existent PM."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            result = package_manager_process_scenario("nonexistent", simple_scenario, output_dir)
            assert result is None
