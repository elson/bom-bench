"""Tests for package manager implementations."""

import tempfile
from pathlib import Path

import pytest

from bom_bench.models.scenario import Scenario, Root, Requirement, ResolverOptions
from bom_bench.package_managers import (
    get_package_manager,
    list_available_package_managers,
    UVPackageManager,
)


class TestPackageManagerRegistry:
    """Test package manager registry functions."""

    def test_list_available_package_managers(self):
        """Test listing available package managers."""
        pms = list_available_package_managers()
        assert isinstance(pms, list)
        assert "uv" in pms

    def test_get_package_manager_uv(self):
        """Test getting UV package manager."""
        pm = get_package_manager("uv")
        assert pm is not None
        assert isinstance(pm, UVPackageManager)
        assert pm.name == "uv"
        assert pm.ecosystem == "python"

    def test_get_package_manager_invalid(self):
        """Test getting non-existent package manager."""
        pm = get_package_manager("nonexistent")
        assert pm is None


class TestUVPackageManager:
    """Test UV package manager implementation."""

    @pytest.fixture
    def uv_pm(self):
        """Create UV package manager instance."""
        return UVPackageManager()

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

    def test_name_and_ecosystem(self, uv_pm):
        """Test UV package manager metadata."""
        assert uv_pm.name == "uv"
        assert uv_pm.ecosystem == "python"

    def test_validate_scenario_packse(self, uv_pm, simple_scenario):
        """Test scenario validation for packse source."""
        assert uv_pm.validate_scenario(simple_scenario) is True

    def test_validate_scenario_other_source(self, uv_pm, simple_scenario):
        """Test scenario validation for non-packse source."""
        simple_scenario.source = "other"
        assert uv_pm.validate_scenario(simple_scenario) is False

    def test_generate_manifest_simple(self, uv_pm, simple_scenario):
        """Test generating simple pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            manifest_path = uv_pm.generate_manifest(simple_scenario, output_dir)

            # Check that file was created
            assert manifest_path.exists()
            assert manifest_path.name == "pyproject.toml"

            # Check content
            content = manifest_path.read_text()
            assert '[project]' in content
            assert 'name = "project"' in content
            assert 'version = "0.1.0"' in content
            assert "'package-a>=1.0.0'" in content
            assert "'package-b<2.0.0'" in content
            assert 'requires-python = ">=3.12"' in content

    def test_generate_manifest_with_environments(self, uv_pm, scenario_with_environments):
        """Test generating pyproject.toml with required environments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            manifest_path = uv_pm.generate_manifest(scenario_with_environments, output_dir)

            # Check content
            content = manifest_path.read_text()
            assert '[project]' in content
            assert '[tool.uv]' in content
            assert 'required-environments' in content
            assert "'python_version >= '3.8''" in content
            assert "'sys_platform == 'linux''" in content

    def test_generate_manifest_creates_directory(self, uv_pm, simple_scenario):
        """Test that generate_manifest creates output directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "nested" / "dir"
            assert not output_dir.exists()

            manifest_path = uv_pm.generate_manifest(simple_scenario, output_dir)

            assert output_dir.exists()
            assert manifest_path.exists()

    def test_get_output_dir(self, uv_pm):
        """Test output directory path generation."""
        base_dir = Path("/tmp/output")
        scenario_name = "test-scenario"

        output_dir = uv_pm.get_output_dir(base_dir, scenario_name)

        assert output_dir == Path("/tmp/output/scenarios/uv/test-scenario")

    def test_supports_source_packse(self, uv_pm):
        """Test that UV supports packse data source."""
        assert uv_pm.supports_source("packse") is True

    def test_supports_source_other(self, uv_pm):
        """Test that UV doesn't support other data sources."""
        assert uv_pm.supports_source("pnpm-tests") is False
        assert uv_pm.supports_source("gradle-testkit") is False
