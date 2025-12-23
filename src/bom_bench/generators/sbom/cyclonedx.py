"""CycloneDX SBOM generator for expected packages."""

from datetime import datetime, timezone
from pathlib import Path
from typing import List

from cyclonedx.model import ExternalReference, ExternalReferenceType, XsUri
from cyclonedx.model.bom import Bom
from cyclonedx.model.component import Component, ComponentType
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
    expected_packages: List[ExpectedPackage],
    output_path: Path
) -> Path:
    """Generate CycloneDX 1.6 SBOM from expected packages.

    Creates a minimal CycloneDX SBOM containing the expected packages
    from a scenario. This serves as groundtruth data for benchmarking
    SCA tools.

    Args:
        scenario_name: Name of scenario (for metadata)
        expected_packages: List of expected packages
        output_path: Where to write expected.cdx.json

    Returns:
        Path to generated SBOM file

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

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate JSON output using CycloneDX 1.6 format
    outputter = JsonV1Dot6(bom)
    json_output = outputter.output_as_string()

    # Write to file
    output_path.write_text(json_output)

    return output_path
