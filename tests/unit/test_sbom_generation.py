"""Tests for SBOM generation."""

import json
import tempfile
from pathlib import Path

import pytest

from bom_bench.generators.sbom.cyclonedx import (
    normalize_package_name,
    create_purl,
    generate_cyclonedx_sbom,
    generate_sbom_result,
    generate_sbom_file,
    generate_meta_file,
)
from bom_bench.models.scenario import ExpectedPackage


class TestPackageNormalization:
    """Test package name normalization."""

    def test_lowercase_conversion(self):
        """Test that package names are converted to lowercase."""
        assert normalize_package_name("Django") == "django"
        assert normalize_package_name("REQUESTS") == "requests"

    def test_underscore_to_hyphen(self):
        """Test that underscores are converted to hyphens."""
        assert normalize_package_name("my_package") == "my-package"
        assert normalize_package_name("test_utils_v2") == "test-utils-v2"

    def test_mixed_normalization(self):
        """Test normalization with both case and underscores."""
        assert normalize_package_name("My_Package") == "my-package"
        assert normalize_package_name("TEST_UTILS") == "test-utils"

    def test_already_normalized(self):
        """Test that normalized names remain unchanged."""
        assert normalize_package_name("requests") == "requests"
        assert normalize_package_name("my-package") == "my-package"


class TestPURLGeneration:
    """Test Package URL (PURL) generation."""

    def test_simple_package(self):
        """Test PURL generation for simple package."""
        package = ExpectedPackage(name="requests", version="2.31.0")
        purl = create_purl(package)
        assert purl.to_string() == "pkg:pypi/requests@2.31.0"

    def test_package_with_uppercase(self):
        """Test PURL generation normalizes uppercase names."""
        package = ExpectedPackage(name="Django", version="4.2.0")
        purl = create_purl(package)
        assert purl.to_string() == "pkg:pypi/django@4.2.0"

    def test_package_with_underscores(self):
        """Test PURL generation converts underscores to hyphens."""
        package = ExpectedPackage(name="my_package", version="1.0.0")
        purl = create_purl(package)
        assert purl.to_string() == "pkg:pypi/my-package@1.0.0"

    def test_package_with_complex_version(self):
        """Test PURL generation with complex version string."""
        package = ExpectedPackage(name="package", version="1.2.3rc1")
        purl = create_purl(package)
        assert purl.to_string() == "pkg:pypi/package@1.2.3rc1"


class TestCycloneDXGeneration:
    """Test CycloneDX SBOM generation."""

    def test_generate_empty_sbom(self):
        """Test generating SBOM with no packages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "expected.cdx.json"
            result = generate_sbom_result(
                scenario_name="test-scenario",
                output_path=output_path,
                packages=[],
                satisfiable=True
            )

            assert result.exists()
            assert result == output_path

            # Validate JSON structure
            with open(result) as f:
                data = json.load(f)

            # Check top-level structure
            assert "satisfiable" in data
            assert data["satisfiable"] is True
            assert "sbom" in data

            sbom = data["sbom"]
            assert sbom["bomFormat"] == "CycloneDX"
            assert sbom["specVersion"] == "1.6"
            assert "metadata" in sbom
            # Components field may not exist if empty, or may be empty list
            components = sbom.get("components", [])
            assert len(components) == 0

    def test_generate_sbom_with_packages(self):
        """Test generating SBOM with packages."""
        packages = [
            ExpectedPackage(name="requests", version="2.31.0"),
            ExpectedPackage(name="urllib3", version="2.0.0"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "expected.cdx.json"
            result = generate_sbom_result(
                scenario_name="test-scenario",
                output_path=output_path,
                packages=packages,
                satisfiable=True
            )

            assert result.exists()

            # Validate JSON structure
            with open(result) as f:
                data = json.load(f)

            # Check top-level structure
            assert "satisfiable" in data
            assert data["satisfiable"] is True
            assert "sbom" in data

            sbom = data["sbom"]
            assert sbom["bomFormat"] == "CycloneDX"
            assert sbom["specVersion"] == "1.6"
            assert len(sbom["components"]) == 2

            # Check first component
            component1 = sbom["components"][0]
            assert component1["type"] == "library"
            assert component1["name"] == "requests"
            assert component1["version"] == "2.31.0"
            assert component1["purl"] == "pkg:pypi/requests@2.31.0"

            # Check second component
            component2 = sbom["components"][1]
            assert component2["type"] == "library"
            assert component2["name"] == "urllib3"
            assert component2["version"] == "2.0.0"
            assert component2["purl"] == "pkg:pypi/urllib3@2.0.0"

    def test_generate_sbom_metadata(self):
        """Test SBOM metadata generation."""
        packages = [ExpectedPackage(name="test-pkg", version="1.0.0")]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "expected.cdx.json"
            result = generate_sbom_result(
                scenario_name="my-test-scenario",
                output_path=output_path,
                packages=packages,
                satisfiable=True
            )

            with open(result) as f:
                data = json.load(f)

            # Check top-level structure
            assert "satisfiable" in data
            assert data["satisfiable"] is True
            assert "sbom" in data

            sbom = data["sbom"]

            # Check metadata
            assert "metadata" in sbom
            metadata = sbom["metadata"]

            # Check timestamp exists and is ISO 8601 format
            assert "timestamp" in metadata
            assert "T" in metadata["timestamp"]

            # Check metadata component
            assert "component" in metadata
            meta_component = metadata["component"]
            assert meta_component["type"] == "application"
            assert meta_component["name"] == "my-test-scenario"
            assert meta_component["version"] == "0.1.0"

    def test_generate_sbom_with_normalized_names(self):
        """Test that package names are normalized in SBOM."""
        packages = [
            ExpectedPackage(name="My_Package", version="1.0.0"),
            ExpectedPackage(name="ANOTHER_PKG", version="2.0.0"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "expected.cdx.json"
            result = generate_sbom_result(
                scenario_name="test-scenario",
                output_path=output_path,
                packages=packages,
                satisfiable=True
            )

            with open(result) as f:
                data = json.load(f)

            # Check top-level structure
            assert "satisfiable" in data
            assert data["satisfiable"] is True
            assert "sbom" in data

            sbom = data["sbom"]

            # Components may be sorted, so check both exist with normalized names
            component_names = {comp["name"] for comp in sbom["components"]}
            assert "my-package" in component_names
            assert "another-pkg" in component_names

            # Check PURLs
            component_purls = {comp["purl"] for comp in sbom["components"]}
            assert "pkg:pypi/my-package@1.0.0" in component_purls
            assert "pkg:pypi/another-pkg@2.0.0" in component_purls

    def test_generate_sbom_creates_directory(self):
        """Test that SBOM generator creates output directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "nested" / "dir" / "expected.cdx.json"
            assert not nested_path.parent.exists()

            packages = [ExpectedPackage(name="test", version="1.0.0")]
            result = generate_sbom_result(
                scenario_name="test",
                output_path=nested_path,
                packages=packages,
                satisfiable=True
            )

            assert nested_path.parent.exists()
            assert result.exists()

    def test_sbom_json_valid(self):
        """Test that generated SBOM is valid JSON."""
        packages = [ExpectedPackage(name="test", version="1.0.0")]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "expected.cdx.json"
            result = generate_sbom_result(
                scenario_name="test",
                output_path=output_path,
                packages=packages,
                satisfiable=True
            )

            # Should not raise exception
            with open(result) as f:
                data = json.load(f)

            # Basic validation
            assert isinstance(data, dict)
            assert "satisfiable" in data
            assert data["satisfiable"] is True
            assert "sbom" in data

            sbom = data["sbom"]
            assert "bomFormat" in sbom
            assert "components" in sbom


class TestGenerateSbomFile:
    """Test pure CycloneDX SBOM file generation (no wrapper)."""

    def test_generate_pure_cyclonedx(self):
        """Test generating pure CycloneDX SBOM without satisfiable wrapper."""
        packages = [
            ExpectedPackage(name="requests", version="2.31.0"),
            ExpectedPackage(name="urllib3", version="2.0.0"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "expected.cdx.json"
            result = generate_sbom_file(
                scenario_name="test-scenario",
                output_path=output_path,
                packages=packages,
            )

            assert result.exists()

            with open(result) as f:
                data = json.load(f)

            # Should be pure CycloneDX - no wrapper
            assert "satisfiable" not in data
            assert "sbom" not in data

            # Top-level should be CycloneDX fields
            assert data["bomFormat"] == "CycloneDX"
            assert data["specVersion"] == "1.6"
            assert "metadata" in data
            assert "components" in data
            assert len(data["components"]) == 2

    def test_generate_empty_sbom(self):
        """Test generating pure SBOM with no packages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "expected.cdx.json"
            result = generate_sbom_file(
                scenario_name="test-scenario",
                output_path=output_path,
                packages=[],
            )

            assert result.exists()

            with open(result) as f:
                data = json.load(f)

            # Pure CycloneDX format
            assert data["bomFormat"] == "CycloneDX"
            components = data.get("components", [])
            assert len(components) == 0

    def test_creates_directory(self):
        """Test that generate_sbom_file creates output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "nested" / "dir" / "expected.cdx.json"
            assert not nested_path.parent.exists()

            packages = [ExpectedPackage(name="test", version="1.0.0")]
            result = generate_sbom_file(
                scenario_name="test",
                output_path=nested_path,
                packages=packages,
            )

            assert nested_path.parent.exists()
            assert result.exists()


class TestGenerateMetaFile:
    """Test meta.json file generation."""

    def test_generate_meta_success(self):
        """Test generating meta.json for successful lock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "meta.json"
            result = generate_meta_file(
                output_path=output_path,
                satisfiable=True,
                exit_code=0,
                stdout="Resolved 5 packages in 1.23s\n",
                stderr="",
            )

            assert result.exists()

            with open(result) as f:
                data = json.load(f)

            assert data["satisfiable"] is True
            assert "package_manager_result" in data

            pm_result = data["package_manager_result"]
            assert pm_result["exit_code"] == 0
            assert pm_result["stdout"] == "Resolved 5 packages in 1.23s\n"
            assert pm_result["stderr"] == ""

    def test_generate_meta_failure(self):
        """Test generating meta.json for failed lock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "meta.json"
            result = generate_meta_file(
                output_path=output_path,
                satisfiable=False,
                exit_code=1,
                stdout="",
                stderr="error: No solution found\n",
            )

            assert result.exists()

            with open(result) as f:
                data = json.load(f)

            assert data["satisfiable"] is False
            pm_result = data["package_manager_result"]
            assert pm_result["exit_code"] == 1
            assert pm_result["stdout"] == ""
            assert pm_result["stderr"] == "error: No solution found\n"

    def test_generate_meta_with_both_streams(self):
        """Test generating meta.json with both stdout and stderr."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "meta.json"
            result = generate_meta_file(
                output_path=output_path,
                satisfiable=True,
                exit_code=0,
                stdout="Resolved packages\n",
                stderr="Warning: deprecated package\n",
            )

            assert result.exists()

            with open(result) as f:
                data = json.load(f)

            pm_result = data["package_manager_result"]
            assert pm_result["stdout"] == "Resolved packages\n"
            assert pm_result["stderr"] == "Warning: deprecated package\n"

    def test_creates_directory(self):
        """Test that generate_meta_file creates output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "nested" / "meta.json"
            assert not nested_path.parent.exists()

            result = generate_meta_file(
                output_path=nested_path,
                satisfiable=True,
                exit_code=0,
                stdout="",
                stderr="",
            )

            assert nested_path.parent.exists()
            assert result.exists()
