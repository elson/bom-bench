"""cdxgen SCA tool plugin for bom-bench.

cdxgen (CycloneDX Generator) is a tool for generating CycloneDX SBOMs
from various package managers and ecosystems.

This plugin provides declarative configuration for cdxgen. The tool is
automatically installed via mise in isolated sandbox environments.

Usage:
    bom-bench benchmark --tools cdxgen

See: https://github.com/CycloneDX/cdxgen
"""

from bom_bench import hookimpl


@hookimpl
def register_sca_tools() -> dict:
    """Register cdxgen as an available SCA tool."""
    return {
        "name": "cdxgen",
        "description": "CycloneDX Generator - creates SBOMs from package manifests",
        "supported_ecosystems": ["python", "javascript", "java", "go", "rust", "dotnet"],
        "homepage": "https://github.com/CycloneDX/cdxgen",
        # Declarative config for sandbox execution
        "tools": [{"name": "npm:@cyclonedx/cdxgen", "version": "11.11"}],
        "command": "cdxgen",
        "args": ["-o", "${OUTPUT_PATH}", "${PROJECT_DIR}"],
        "env": {},
    }
