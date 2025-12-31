"""SBOM (Software Bill of Materials) generators."""

from bom_bench.generators.sbom.cyclonedx import generate_cyclonedx_sbom

__all__ = ["generate_cyclonedx_sbom"]
