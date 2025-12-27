"""CycloneDX SBOM generator for expected packages."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

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


def create_purl(package: ExpectedPackage) -> PackageURL:
    """Create Package URL (PURL) for a Python package.

    Args:
        package: Expected package

    Returns:
        PackageURL object for the package
    """
    normalized_name = normalize_package_name(package.name)
    purl = PackageURL(
        type="pypi",
        name=normalized_name,
        version=package.version
    )
    return purl


def generate_cyclonedx_sbom(
    scenario_name: str,
    expected_packages: List[ExpectedPackage]
) -> Dict[str, Any]:
    """Generate CycloneDX 1.6 SBOM from expected packages.

    Creates a minimal CycloneDX SBOM containing the expected packages
    from a scenario. This serves as groundtruth data for benchmarking
    SCA tools.

    Args:
        scenario_name: Name of scenario (for metadata)
        expected_packages: List of expected packages

    Returns:
        Dictionary containing the SBOM data (ordered)

    Raises:
        Exception: If SBOM generation or validation fails
    """
    # Create metadata component (the root application)
    metadata_component = Component(
        type=ComponentType.APPLICATION,
        name=scenario_name,
        version="0.1.0"
    )

    # Create BOM with metadata
    bom = Bom()
    bom.metadata.component = metadata_component
    bom.metadata.timestamp = datetime.now(timezone.utc)

    # Add external reference to bom-bench
    bom_bench_ref = ExternalReference(
        type=ExternalReferenceType.BUILD_SYSTEM,
        url=XsUri("https://github.com/your-org/bom-bench")
    )
    bom.metadata.component.external_references.add(bom_bench_ref)

    # Track component references for dependency graph
    component_refs = []

    # Add components from expected packages
    for package in expected_packages:
        purl = create_purl(package)

        component = Component(
            type=ComponentType.LIBRARY,
            name=normalize_package_name(package.name),
            version=package.version,
            purl=purl
        )

        bom.components.add(component)
        component_refs.append(component.bom_ref)

    # Build dependency graph
    # Root component depends on all library components
    root_dependency = Dependency(ref=metadata_component.bom_ref)
    for component_ref in component_refs:
        root_dependency.dependencies.add(Dependency(ref=component_ref))
    bom.dependencies.add(root_dependency)

    # Add empty dependency entries for each library component
    for component_ref in component_refs:
        bom.dependencies.add(Dependency(ref=component_ref))

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


def generate_sbom_result(
    scenario_name: str,
    output_path: Path,
    packages: Optional[List[ExpectedPackage]] = None,
    satisfiable: bool = True
) -> Path:
    """Generate SBOM result file with satisfiable status.

    Creates a JSON file containing:
    - satisfiable: Whether the scenario was satisfiable (lock succeeded)
    - sbom: CycloneDX SBOM (only if satisfiable and packages provided)

    Args:
        scenario_name: Name of scenario (for metadata)
        output_path: Where to write expected.cdx.json
        packages: List of resolved packages (None if lock failed)
        satisfiable: Whether resolution was satisfiable

    Returns:
        Path to generated file

    Raises:
        Exception: If file generation fails
    """
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result: Dict[str, Any] = {"satisfiable": satisfiable}

    # Only include SBOM if satisfiable and packages is not None (empty list is ok)
    if satisfiable and packages is not None:
        sbom = generate_cyclonedx_sbom(scenario_name, packages)
        result["sbom"] = sbom

    # Write formatted JSON
    json_output = json.dumps(result, indent=2)
    output_path.write_text(json_output)

    return output_path


def generate_sbom_file(
    scenario_name: str,
    output_path: Path,
    packages: List[ExpectedPackage],
) -> Path:
    """Generate pure CycloneDX SBOM file (no wrapper).

    Creates a JSON file containing only the CycloneDX SBOM data,
    without the satisfiable wrapper. The satisfiable status is
    stored separately in meta.json.

    Args:
        scenario_name: Name of scenario (for metadata)
        output_path: Where to write expected.cdx.json
        packages: List of resolved packages

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
        }
    }

    # Write formatted JSON
    json_output = json.dumps(meta, indent=2)
    output_path.write_text(json_output)

    return output_path
