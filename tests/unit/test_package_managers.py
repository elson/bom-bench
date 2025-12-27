"""Tests for package manager implementations."""

import tempfile
from pathlib import Path

import pytest

from bom_bench.models.scenario import Scenario, Root, Requirement, ResolverOptions
from bom_bench.models.result import LockResult, LockStatus
from bom_bench.plugins import (
    pm_get_output_dir,
    pm_validate_scenario,
    pm_generate_sbom_for_lock,
    pm_generate_manifest,
    list_available_package_managers,
    check_pm_available,
    reset_plugins,
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
        assert check_pm_available("uv") is True

    def test_check_pm_available_invalid(self):
        """Test checking non-existent package manager."""
        assert check_pm_available("nonexistent") is False


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

    def test_validate_scenario_packse(self, simple_scenario):
        """Test scenario validation for packse source."""
        assert pm_validate_scenario("uv", simple_scenario) is True

    def test_validate_scenario_other_source(self, simple_scenario):
        """Test scenario validation for non-packse source."""
        simple_scenario.source = "other"
        assert pm_validate_scenario("uv", simple_scenario) is False

    def test_validate_scenario_invalid_pm(self, simple_scenario):
        """Test scenario validation for non-existent PM."""
        assert pm_validate_scenario("nonexistent", simple_scenario) is False

    def test_generate_manifest_simple(self, simple_scenario):
        """Test generating simple pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            manifest_path = pm_generate_manifest("uv", simple_scenario, output_dir)

            # Check that file was created
            assert manifest_path is not None
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

    def test_generate_manifest_with_environments(self, scenario_with_environments):
        """Test generating pyproject.toml with required environments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            manifest_path = pm_generate_manifest("uv", scenario_with_environments, output_dir)

            # Check content
            assert manifest_path is not None
            content = manifest_path.read_text()
            assert '[project]' in content
            assert '[tool.uv]' in content
            assert 'required-environments' in content
            assert "'python_version >= '3.8''" in content
            assert "'sys_platform == 'linux''" in content

    def test_generate_manifest_creates_directory(self, simple_scenario):
        """Test that generate_manifest creates output directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "nested" / "dir"
            assert not output_dir.exists()

            manifest_path = pm_generate_manifest("uv", simple_scenario, output_dir)

            assert manifest_path is not None
            assert output_dir.exists()
            assert manifest_path.exists()

    def test_get_output_dir(self):
        """Test output directory path generation."""
        base_dir = Path("/tmp/output")
        scenario_name = "test-scenario"

        output_dir = pm_get_output_dir("uv", base_dir, scenario_name)

        assert output_dir == Path("/tmp/output/scenarios/uv/test-scenario")

    def test_get_output_dir_invalid_pm(self):
        """Test output directory for non-existent PM."""
        output_dir = pm_get_output_dir("nonexistent", Path("/tmp"), "test")
        assert output_dir is None

    def test_generate_sbom_for_lock_success(self, simple_scenario):
        """Test SBOM generation for successful lock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            assets_dir = output_dir / "assets"
            assets_dir.mkdir(parents=True)

            # Create a mock uv.lock file
            lock_content = """
version = 1
requires-python = ">=3.12"

[[package]]
name = "package-a"
version = "1.0.0"
source = { registry = "https://test.pypi.org" }
"""
            (assets_dir / "uv.lock").write_text(lock_content)

            lock_result = LockResult(
                scenario_name="test-scenario",
                package_manager="uv",
                status=LockStatus.SUCCESS,
                exit_code=0,
                stdout="Resolved 1 package",
                stderr="",
                duration_seconds=0.5
            )

            sbom_path = pm_generate_sbom_for_lock("uv", simple_scenario, output_dir, lock_result)

            # Should generate expected.cdx.json
            assert sbom_path is not None
            expected_sbom = output_dir / "expected.cdx.json"
            assert expected_sbom.exists()

            # Should also generate meta.json
            meta_path = output_dir / "meta.json"
            assert meta_path.exists()

    def test_generate_sbom_for_lock_failure(self, simple_scenario):
        """Test SBOM generation for failed lock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            lock_result = LockResult(
                scenario_name="test-scenario",
                package_manager="uv",
                status=LockStatus.FAILED,
                exit_code=1,
                stdout="",
                stderr="Resolution failed",
                duration_seconds=0.5
            )

            result_path = pm_generate_sbom_for_lock("uv", simple_scenario, output_dir, lock_result)

            # Should generate meta.json but NOT expected.cdx.json
            meta_path = output_dir / "meta.json"
            assert meta_path.exists()

            # Should NOT generate expected.cdx.json for failed lock
            expected_sbom = output_dir / "expected.cdx.json"
            assert not expected_sbom.exists()

    def test_generate_sbom_for_lock_invalid_pm(self, simple_scenario):
        """Test SBOM generation for non-existent PM."""
        lock_result = LockResult(
            scenario_name="test-scenario",
            package_manager="nonexistent",
            status=LockStatus.SUCCESS,
            exit_code=0,
            stdout="",
            stderr="",
            duration_seconds=0.5
        )

        result = pm_generate_sbom_for_lock("nonexistent", simple_scenario, Path("/tmp"), lock_result)
        assert result is None
