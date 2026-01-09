"""Snyk SCA tool plugin for bom-bench.

Snyk is a security testing tool that can analyze dependencies and identify
vulnerabilities. This plugin uses the Snyk CLI's `snyk test` command with
--print-deps and --json flags to extract dependency information.

Note: Snyk's JSON output format is non-standard (two concatenated JSON objects),
requiring custom parsing logic.

Usage:
    bom-bench benchmark --tools snyk

Requirements:
    - SNYK_TOKEN environment variable must be set for authentication

See: https://docs.snyk.io/
"""

import json

from bom_bench import hookimpl


@hookimpl
def register_sca_tools() -> dict:
    """Register Snyk as an available SCA tool."""
    return {
        "name": "snyk",
        "description": "Snyk CLI - security testing and dependency analysis",
        "supported_ecosystems": [
            "python",
            "javascript",
            "java",
            "go",
            "ruby",
            "php",
            "dotnet",
        ],
        "homepage": "https://docs.snyk.io/",
        "tools": [{"name": "npm:snyk", "version": "1.1301.2"}],
        "command": "snyk",
        "args": [
            "test",
            "${PROJECT_DIR}",
            "--print-deps",
            "--json",
            ">",
            "${OUTPUT_PATH}",
            "||",
            "true",
        ],
        "env": {"SNYK_TOKEN": "${SNYK_TOKEN}"},
    }


def _extract_dependencies(dep_tree: dict) -> list[dict]:
    """Recursively extract name/version from arbitrarily nested dependencies."""
    packages = []

    if "name" in dep_tree and "version" in dep_tree:
        name = str(dep_tree["name"]).strip()
        version = str(dep_tree["version"]).strip()
        if name and version:
            packages.append({"name": name, "version": version})

    if "dependencies" in dep_tree:
        for dep in dep_tree["dependencies"].values():
            packages.extend(_extract_dependencies(dep))

    return packages


def _parse_snyk_output(raw_output: str) -> list[dict]:
    """Parse Snyk's badly-formed JSON output (two concatenated JSON objects).

    Snyk outputs `{first}{second}` format where:
    - First object: dependency tree
    - Second object: vulnerabilities (ignored)
    """
    try:
        decoder = json.JSONDecoder()
        first_obj, _ = decoder.raw_decode(raw_output.strip())
    except (json.JSONDecodeError, ValueError):
        return []

    if first_obj.get("ok") is False:
        return []

    packages = _extract_dependencies(first_obj)

    seen = set()
    unique_packages = []
    for pkg in packages:
        key = (pkg["name"], pkg["version"])
        if key not in seen:
            seen.add(key)
            unique_packages.append(pkg)

    return unique_packages


@hookimpl
def handle_sca_tool_response(bom_bench, stdout, stderr, output_file_contents):
    """Parse Snyk JSON output and generate CycloneDX SBOM."""
    _ = stderr
    raw_output = output_file_contents or stdout

    if not raw_output or not raw_output.strip():
        return None

    packages = _parse_snyk_output(raw_output)

    if not packages:
        return None

    sbom = bom_bench.generate_cyclonedx_sbom("snyk-project", packages)
    return json.dumps(sbom, indent=2)
