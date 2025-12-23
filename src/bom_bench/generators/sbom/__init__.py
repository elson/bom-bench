"""SBOM (Software Bill of Materials) generators."""

from bom_bench.generators.sbom.cyclonedx import (
    generate_cyclonedx_sbom,
    generate_sbom_result,
)

__all__ = ["generate_cyclonedx_sbom", "generate_sbom_result"]
