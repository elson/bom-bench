"""Tests for SBOM comparison logic."""

import json
import pytest
from pathlib import Path

from bom_bench.benchmarking.comparison import (
    normalize_purl,
    extract_purls_from_cyclonedx,
    load_expected_sbom,
    load_actual_sbom,
    compare_sboms,
    load_scenario_meta,
)


class TestNormalizePurl:
    """Tests for PURL normalization."""

    def test_normalize_pypi_lowercase(self):
        """Test PyPI package name lowercasing."""
        purl = "pkg:pypi/MyPackage@1.0.0"
        normalized = normalize_purl(purl)
        assert normalized == "pkg:pypi/mypackage@1.0.0"

    def test_normalize_pypi_underscore_to_hyphen(self):
        """Test PyPI underscore to hyphen conversion."""
        purl = "pkg:pypi/my_package@1.0.0"
        normalized = normalize_purl(purl)
        assert normalized == "pkg:pypi/my-package@1.0.0"

    def test_normalize_pypi_mixed(self):
        """Test PyPI mixed normalization."""
        purl = "pkg:pypi/My_Package_Name@2.0.0"
        normalized = normalize_purl(purl)
        assert normalized == "pkg:pypi/my-package-name@2.0.0"

    def test_normalize_npm_lowercase_only(self):
        """Test that non-PyPI packages only get lowercase (no underscore conversion)."""
        purl = "pkg:npm/My_Package@1.0.0"
        normalized = normalize_purl(purl)
        # npm packages get lowercase but keep underscores (only PyPI converts _ to -)
        assert normalized == "pkg:npm/my_package@1.0.0"

    def test_normalize_removes_qualifiers(self):
        """Test that qualifiers are removed."""
        purl = "pkg:pypi/package@1.0.0?vcs_url=https://github.com/..."
        normalized = normalize_purl(purl)
        assert "?" not in normalized
        assert normalized == "pkg:pypi/package@1.0.0"

    def test_normalize_invalid_purl(self):
        """Test that invalid PURLs raise ValueError."""
        with pytest.raises(ValueError):
            normalize_purl("not-a-purl")


class TestExtractPurls:
    """Tests for PURL extraction from CycloneDX SBOMs."""

    def test_extract_from_empty_sbom(self):
        """Test extraction from empty SBOM."""
        sbom = {"components": []}
        purls = extract_purls_from_cyclonedx(sbom)
        assert purls == set()

    def test_extract_from_sbom_without_components(self):
        """Test extraction from SBOM without components key."""
        sbom = {"bomFormat": "CycloneDX"}
        purls = extract_purls_from_cyclonedx(sbom)
        assert purls == set()

    def test_extract_single_purl(self):
        """Test extraction of single PURL."""
        sbom = {
            "components": [
                {"name": "pkg", "version": "1.0", "purl": "pkg:pypi/package@1.0.0"}
            ]
        }
        purls = extract_purls_from_cyclonedx(sbom)
        assert len(purls) == 1
        assert "pkg:pypi/package@1.0.0" in purls

    def test_extract_multiple_purls(self):
        """Test extraction of multiple PURLs."""
        sbom = {
            "components": [
                {"name": "a", "purl": "pkg:pypi/package-a@1.0.0"},
                {"name": "b", "purl": "pkg:pypi/package-b@2.0.0"},
                {"name": "c", "purl": "pkg:pypi/package-c@3.0.0"},
            ]
        }
        purls = extract_purls_from_cyclonedx(sbom)
        assert len(purls) == 3

    def test_extract_skips_invalid_purls(self):
        """Test that invalid PURLs are skipped."""
        sbom = {
            "components": [
                {"name": "good", "purl": "pkg:pypi/good@1.0.0"},
                {"name": "bad", "purl": "not-a-valid-purl"},
                {"name": "missing"},  # No purl key
            ]
        }
        purls = extract_purls_from_cyclonedx(sbom)
        assert len(purls) == 1
        assert "pkg:pypi/good@1.0.0" in purls

    def test_extract_normalizes_purls(self):
        """Test that extracted PURLs are normalized."""
        sbom = {
            "components": [
                {"name": "pkg", "purl": "pkg:pypi/My_Package@1.0.0"}
            ]
        }
        purls = extract_purls_from_cyclonedx(sbom)
        assert "pkg:pypi/my-package@1.0.0" in purls

    def test_extract_filters_root_project(self):
        """Test that root project component is filtered out.

        Some SCA tools (like Syft) include the root project as a component,
        while others (like cdxgen) don't. This should be filtered out to
        ensure fair comparison.
        """
        sbom = {
            "components": [
                # Root project - should be filtered
                {"name": "project", "version": "0.1.0", "purl": "pkg:pypi/project@0.1.0"},
                # Actual dependencies - should be kept
                {"name": "requests", "purl": "pkg:pypi/requests@2.28.0"},
                {"name": "click", "purl": "pkg:pypi/click@8.0.0"},
            ]
        }
        purls = extract_purls_from_cyclonedx(sbom)

        # Root project should be filtered out
        assert "pkg:pypi/project@0.1.0" not in purls
        # Dependencies should remain
        assert "pkg:pypi/requests@2.28.0" in purls
        assert "pkg:pypi/click@8.0.0" in purls
        assert len(purls) == 2


class TestLoadExpectedSbom:
    """Tests for loading expected SBOMs."""

    def test_load_satisfiable_sbom(self, tmp_path):
        """Test loading a satisfiable expected SBOM."""
        sbom_path = tmp_path / "expected.cdx.json"
        sbom_data = {
            "satisfiable": True,
            "sbom": {
                "bomFormat": "CycloneDX",
                "components": [
                    {"name": "pkg", "purl": "pkg:pypi/package@1.0.0"}
                ]
            }
        }
        sbom_path.write_text(json.dumps(sbom_data))

        sbom, satisfiable = load_expected_sbom(sbom_path)

        assert satisfiable is True
        assert sbom is not None
        assert "components" in sbom

    def test_load_unsatisfiable_sbom(self, tmp_path):
        """Test loading an unsatisfiable expected SBOM."""
        sbom_path = tmp_path / "expected.cdx.json"
        sbom_data = {"satisfiable": False}
        sbom_path.write_text(json.dumps(sbom_data))

        sbom, satisfiable = load_expected_sbom(sbom_path)

        assert satisfiable is False
        assert sbom is None

    def test_load_missing_file(self, tmp_path):
        """Test loading a non-existent file."""
        sbom_path = tmp_path / "nonexistent.json"

        sbom, satisfiable = load_expected_sbom(sbom_path)

        assert sbom is None
        assert satisfiable is True  # Default

    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON."""
        sbom_path = tmp_path / "invalid.json"
        sbom_path.write_text("not valid json")

        sbom, satisfiable = load_expected_sbom(sbom_path)

        assert sbom is None
        assert satisfiable is True  # Default


class TestLoadActualSbom:
    """Tests for loading actual SBOMs."""

    def test_load_valid_sbom(self, tmp_path):
        """Test loading a valid actual SBOM."""
        sbom_path = tmp_path / "actual.cdx.json"
        sbom_data = {
            "bomFormat": "CycloneDX",
            "components": [
                {"name": "pkg", "purl": "pkg:pypi/package@1.0.0"}
            ]
        }
        sbom_path.write_text(json.dumps(sbom_data))

        sbom = load_actual_sbom(sbom_path)

        assert sbom is not None
        assert sbom["bomFormat"] == "CycloneDX"

    def test_load_missing_file(self, tmp_path):
        """Test loading a non-existent file."""
        sbom_path = tmp_path / "nonexistent.json"

        sbom = load_actual_sbom(sbom_path)

        assert sbom is None

    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON."""
        sbom_path = tmp_path / "invalid.json"
        sbom_path.write_text("not valid json")

        sbom = load_actual_sbom(sbom_path)

        assert sbom is None


class TestCompareSboms:
    """Tests for SBOM comparison."""

    def test_compare_matching_sboms(self, tmp_path):
        """Test comparing matching SBOMs."""
        expected_path = tmp_path / "expected.cdx.json"
        actual_path = tmp_path / "actual.cdx.json"

        expected_data = {
            "satisfiable": True,
            "sbom": {
                "components": [
                    {"purl": "pkg:pypi/package-a@1.0.0"},
                    {"purl": "pkg:pypi/package-b@2.0.0"},
                ]
            }
        }
        actual_data = {
            "components": [
                {"purl": "pkg:pypi/package-a@1.0.0"},
                {"purl": "pkg:pypi/package-b@2.0.0"},
            ]
        }

        expected_path.write_text(json.dumps(expected_data))
        actual_path.write_text(json.dumps(actual_data))

        expected_purls, actual_purls, satisfiable = compare_sboms(
            expected_path, actual_path
        )

        assert satisfiable is True
        assert expected_purls == actual_purls
        assert len(expected_purls) == 2

    def test_compare_unsatisfiable(self, tmp_path):
        """Test comparing with unsatisfiable expected."""
        expected_path = tmp_path / "expected.cdx.json"
        actual_path = tmp_path / "actual.cdx.json"

        expected_data = {"satisfiable": False}
        actual_data = {"components": []}

        expected_path.write_text(json.dumps(expected_data))
        actual_path.write_text(json.dumps(actual_data))

        expected_purls, actual_purls, satisfiable = compare_sboms(
            expected_path, actual_path
        )

        assert satisfiable is False
        assert expected_purls == set()

    def test_compare_with_differences(self, tmp_path):
        """Test comparing SBOMs with differences."""
        expected_path = tmp_path / "expected.cdx.json"
        actual_path = tmp_path / "actual.cdx.json"

        expected_data = {
            "satisfiable": True,
            "sbom": {
                "components": [
                    {"purl": "pkg:pypi/a@1.0.0"},
                    {"purl": "pkg:pypi/b@2.0.0"},
                ]
            }
        }
        actual_data = {
            "components": [
                {"purl": "pkg:pypi/a@1.0.0"},
                {"purl": "pkg:pypi/c@3.0.0"},
            ]
        }

        expected_path.write_text(json.dumps(expected_data))
        actual_path.write_text(json.dumps(actual_data))

        expected_purls, actual_purls, satisfiable = compare_sboms(
            expected_path, actual_path
        )

        assert satisfiable is True
        # a is in both (TP)
        # b is only in expected (FN)
        # c is only in actual (FP)
        assert "pkg:pypi/a@1.0.0" in expected_purls
        assert "pkg:pypi/a@1.0.0" in actual_purls
        assert "pkg:pypi/b@2.0.0" in expected_purls
        assert "pkg:pypi/b@2.0.0" not in actual_purls
        assert "pkg:pypi/c@3.0.0" in actual_purls
        assert "pkg:pypi/c@3.0.0" not in expected_purls


class TestLoadScenarioMeta:
    """Tests for loading scenario meta.json."""

    def test_load_valid_meta(self, tmp_path):
        """Test loading a valid meta.json file."""
        meta_path = tmp_path / "meta.json"
        meta_data = {
            "satisfiable": True,
            "package_manager_result": {
                "exit_code": 0,
                "stdout": "Resolved 5 packages\n",
                "stderr": ""
            }
        }
        meta_path.write_text(json.dumps(meta_data))

        meta = load_scenario_meta(meta_path)

        assert meta is not None
        assert meta["satisfiable"] is True
        assert meta["package_manager_result"]["exit_code"] == 0
        assert meta["package_manager_result"]["stdout"] == "Resolved 5 packages\n"

    def test_load_unsatisfiable_meta(self, tmp_path):
        """Test loading meta.json with unsatisfiable scenario."""
        meta_path = tmp_path / "meta.json"
        meta_data = {
            "satisfiable": False,
            "package_manager_result": {
                "exit_code": 1,
                "stdout": "",
                "stderr": "No solution found\n"
            }
        }
        meta_path.write_text(json.dumps(meta_data))

        meta = load_scenario_meta(meta_path)

        assert meta is not None
        assert meta["satisfiable"] is False
        assert meta["package_manager_result"]["exit_code"] == 1

    def test_load_missing_meta(self, tmp_path):
        """Test loading non-existent meta.json."""
        meta_path = tmp_path / "nonexistent.json"

        meta = load_scenario_meta(meta_path)

        assert meta is None

    def test_load_invalid_json_meta(self, tmp_path):
        """Test loading invalid JSON meta file."""
        meta_path = tmp_path / "meta.json"
        meta_path.write_text("not valid json")

        meta = load_scenario_meta(meta_path)

        assert meta is None


class TestLoadExpectedSbomPureCycloneDX:
    """Tests for loading pure CycloneDX expected SBOMs (new format)."""

    def test_load_pure_cyclonedx_sbom(self, tmp_path):
        """Test loading pure CycloneDX SBOM without wrapper."""
        sbom_path = tmp_path / "expected.cdx.json"
        sbom_data = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "components": [
                {"name": "pkg", "purl": "pkg:pypi/package@1.0.0"}
            ]
        }
        sbom_path.write_text(json.dumps(sbom_data))

        # Need corresponding meta.json
        meta_path = tmp_path / "meta.json"
        meta_data = {"satisfiable": True, "package_manager_result": {"exit_code": 0, "stdout": "", "stderr": ""}}
        meta_path.write_text(json.dumps(meta_data))

        sbom, satisfiable = load_expected_sbom(sbom_path, meta_path)

        assert satisfiable is True
        assert sbom is not None
        assert sbom["bomFormat"] == "CycloneDX"
        assert "components" in sbom

    def test_load_pure_cyclonedx_unsatisfiable(self, tmp_path):
        """Test loading when meta.json indicates unsatisfiable."""
        # SBOM file may not exist for unsatisfiable scenarios
        sbom_path = tmp_path / "expected.cdx.json"

        meta_path = tmp_path / "meta.json"
        meta_data = {"satisfiable": False, "package_manager_result": {"exit_code": 1, "stdout": "", "stderr": "No solution"}}
        meta_path.write_text(json.dumps(meta_data))

        sbom, satisfiable = load_expected_sbom(sbom_path, meta_path)

        assert satisfiable is False
        assert sbom is None
