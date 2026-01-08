"""CycloneDX SBOM generator for expected packages."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cyclonedx.model import ExternalReference, ExternalReferenceType, XsUri
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.model.dependency import Dependency
from cyclonedx.output.json import JsonV1Dot6
from packageurl import PackageURL

from bom_bench.models.scenario import ExpectedPackage


def normalize_package_name(name: str) -> str:
    """Normalize Python package name for PURL.

    Per PEP 503, package names should be lowercase with hyphens.

    Args:
        name: Original package name

    Returns:
        Normalized package name
    """
    return name.lower().replace("_", "-")


def _get_package_name(package: ExpectedPackage | dict) -> str:
    """Get package name from ExpectedPackage or dict."""
    return package["name"] if isinstance(package, dict) else package.name


def _get_package_version(package: ExpectedPackage | dict) -> str:
    """Get package version from ExpectedPackage or dict."""
    return package["version"] if isinstance(package, dict) else package.version


def create_purl(package: ExpectedPackage | dict) -> PackageURL:
    """Create Package URL (PURL) for a Python package.

    Args:
        package: Expected package (dict or ExpectedPackage)

    Returns:
        PackageURL object for the package
    """
    name = _get_package_name(package)
    version = _get_package_version(package)
    normalized_name = normalize_package_name(name)
    purl = PackageURL(type="pypi", name=normalized_name, version=version)
    return purl


def generate_cyclonedx_sbom(
    scenario_name: str, expected_packages: list[ExpectedPackage] | list[dict]
) -> dict[str, Any]:
    """Generate CycloneDX 1.6 SBOM from expected packages.

    Creates a minimal CycloneDX SBOM containing the expected packages
    from a scenario. This serves as groundtruth data for benchmarking
    SCA tools.

    Args:
        scenario_name: Name of scenario (for metadata)
        expected_packages: List of expected packages (dicts or ExpectedPackage objects)

    Returns:
        Dictionary containing the SBOM data (ordered)

    Raises:
        Exception: If SBOM generation or validation fails
    """
    # Create metadata component (the root application)
    # pyright/type: ignore comments suppress false positives from incomplete cyclonedx type stubs
    metadata_component = Component(  # pyright: ignore  # type: ignore
        type=ComponentType.APPLICATION, name=scenario_name, version="0.1.0"
    )

    # Create BOM with metadata
    bom = Bom()
    bom.metadata.component = metadata_component  # pyright: ignore  # type: ignore
    bom.metadata.timestamp = datetime.now(UTC)  # pyright: ignore  # type: ignore

    # Add external reference to bom-bench
    bom_bench_ref = ExternalReference(  # pyright: ignore  # type: ignore
        type=ExternalReferenceType.BUILD_SYSTEM, url=XsUri("https://github.com/elson/bom-bench")
    )
    bom.metadata.component.external_references.add(bom_bench_ref)  # pyright: ignore  # type: ignore

    # Track component references for dependency graph
    component_refs = []

    # Add components from expected packages
    for package in expected_packages:
        purl = create_purl(package)
        name = _get_package_name(package)
        version = _get_package_version(package)

        component = Component(  # pyright: ignore  # type: ignore
            type=ComponentType.LIBRARY,
            name=normalize_package_name(name),
            version=version,
            purl=purl,
        )

        bom.components.add(component)  # pyright: ignore  # type: ignore
        component_refs.append(component.bom_ref)  # pyright: ignore  # type: ignore

    # Build dependency graph
    # Root component depends on all library components
    root_dependency = Dependency(ref=metadata_component.bom_ref)  # pyright: ignore  # type: ignore
    for component_ref in component_refs:
        root_dependency.dependencies.add(Dependency(ref=component_ref))  # pyright: ignore  # type: ignore
    bom.dependencies.add(root_dependency)  # pyright: ignore  # type: ignore

    # Add empty dependency entries for each library component
    for component_ref in component_refs:
        bom.dependencies.add(Dependency(ref=component_ref))  # pyright: ignore  # type: ignore

    # Generate JSON output using CycloneDX 1.6 format
    outputter = JsonV1Dot6(bom)
    json_output = outputter.output_as_string()

    # Parse and reformat to ensure proper ordering and formatting
    sbom_dict = json.loads(json_output)

    # Reorder to put metadata and dependencies first
    ordered_sbom = {}
    if "bomFormat" in sbom_dict:
        ordered_sbom["bomFormat"] = sbom_dict["bomFormat"]
    if "specVersion" in sbom_dict:
        ordered_sbom["specVersion"] = sbom_dict["specVersion"]
    if "version" in sbom_dict:
        ordered_sbom["version"] = sbom_dict["version"]
    if "$schema" in sbom_dict:
        ordered_sbom["$schema"] = sbom_dict["$schema"]
    if "metadata" in sbom_dict:
        ordered_sbom["metadata"] = sbom_dict["metadata"]
    if "dependencies" in sbom_dict:
        ordered_sbom["dependencies"] = sbom_dict["dependencies"]
    if "components" in sbom_dict:
        ordered_sbom["components"] = sbom_dict["components"]

    # Add any remaining fields
    for key, value in sbom_dict.items():
        if key not in ordered_sbom:
            ordered_sbom[key] = value

    return ordered_sbom


def generate_sbom_file(
    scenario_name: str,
    output_path: Path,
    packages: list[ExpectedPackage] | list[dict],
) -> Path:
    """Generate pure CycloneDX SBOM file (no wrapper).

    Creates a JSON file containing only the CycloneDX SBOM data,
    without the satisfiable wrapper. The satisfiable status is
    stored separately in meta.json.

    Args:
        scenario_name: Name of scenario (for metadata)
        output_path: Where to write expected.cdx.json
        packages: List of resolved packages (dicts or ExpectedPackage objects)

    Returns:
        Path to generated file

    Raises:
        Exception: If file generation fails
    """
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate pure CycloneDX SBOM
    sbom = generate_cyclonedx_sbom(scenario_name, packages)

    # Write formatted JSON
    json_output = json.dumps(sbom, indent=2)
    output_path.write_text(json_output)

    return output_path


def generate_meta_file(
    output_path: Path,
    satisfiable: bool,
    exit_code: int,
    stdout: str,
    stderr: str,
) -> Path:
    """Generate scenario meta.json file.

    Creates a JSON file containing scenario metadata including
    the satisfiable status and package manager execution results.

    Args:
        output_path: Where to write meta.json
        satisfiable: Whether the scenario was satisfiable
        exit_code: Package manager process exit code
        stdout: Package manager stdout content
        stderr: Package manager stderr content

    Returns:
        Path to generated file

    Raises:
        Exception: If file generation fails
    """
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    meta = {
        "satisfiable": satisfiable,
        "package_manager_result": {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
        },
    }

    # Write formatted JSON
    json_output = json.dumps(meta, indent=2)
    output_path.write_text(json_output)

    return output_path
