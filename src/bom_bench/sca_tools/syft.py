"""Syft SCA tool plugin for bom-bench.

Syft is an SBOM generation tool by Anchore that creates bill of materials
from container images and filesystems.

This plugin provides declarative configuration for Syft. The tool is
automatically installed via mise in isolated sandbox environments.

Usage:
    bom-bench benchmark --tools syft

See: https://github.com/anchore/syft
"""

from bom_bench import hookimpl


@hookimpl
def register_sca_tools() -> dict:
    """Register Syft as an available SCA tool."""
    return {
        "name": "syft",
        "description": "Anchore Syft - SBOM generator for containers and filesystems",
        "supported_ecosystems": [
            "python",
            "javascript",
            "java",
            "go",
            "rust",
            "ruby",
            "php",
            "dotnet",
        ],
        "homepage": "https://github.com/anchore/syft",
        # Declarative config for sandbox execution
        "tools": [{"name": "syft", "version": "latest"}],
        "command": "syft",
        "args": ["${PROJECT_DIR}", "-o", "cyclonedx-json=${OUTPUT_PATH}"],
        "env": {},
    }
