"""Tests for SBOM generation."""

import json
import tempfile
from pathlib import Path

import pytest

from bom_bench.generators.sbom.cyclonedx import (
    normalize_package_name,
    create_purl,
    generate_cyclonedx_sbom,
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
            result = generate_cyclonedx_sbom(
                scenario_name="test-scenario",
                expected_packages=[],
                output_path=output_path
            )

            assert result.exists()
            assert result == output_path

            # Validate JSON structure
            with open(result) as f:
                sbom = json.load(f)

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
            result = generate_cyclonedx_sbom(
                scenario_name="test-scenario",
                expected_packages=packages,
                output_path=output_path
            )

            assert result.exists()

            # Validate JSON structure
            with open(result) as f:
                sbom = json.load(f)

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
            result = generate_cyclonedx_sbom(
                scenario_name="my-test-scenario",
                expected_packages=packages,
                output_path=output_path
            )

            with open(result) as f:
                sbom = json.load(f)

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
            result = generate_cyclonedx_sbom(
                scenario_name="test-scenario",
                expected_packages=packages,
                output_path=output_path
            )

            with open(result) as f:
                sbom = json.load(f)

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
            result = generate_cyclonedx_sbom(
                scenario_name="test",
                expected_packages=packages,
                output_path=nested_path
            )

            assert nested_path.parent.exists()
            assert result.exists()

    def test_sbom_json_valid(self):
        """Test that generated SBOM is valid JSON."""
        packages = [ExpectedPackage(name="test", version="1.0.0")]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "expected.cdx.json"
            result = generate_cyclonedx_sbom(
                scenario_name="test",
                expected_packages=packages,
                output_path=output_path
            )

            # Should not raise exception
            with open(result) as f:
                data = json.load(f)

            # Basic validation
            assert isinstance(data, dict)
            assert "bomFormat" in data
            assert "components" in data
