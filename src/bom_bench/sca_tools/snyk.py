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

PACKAGE_MANAGER_PURL_TYPE_MAP = {
    "npm": "npm",
    "yarn": "npm",
    "pnpm": "npm",
    "pip": "pypi",
    "poetry": "pypi",
    "uv": "pypi",
    "maven": "maven",
    "go": "golang",
    "rubygems": "gem",
    "composer": "composer",
    "nuget": "nuget",
}

PURL_TYPE_DEFAULT = "generic"


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
            "--print-graph",
            "--json",
            ">",
            "${OUTPUT_PATH}",
            "||",
            "true",
        ],
        "env": {"SNYK_TOKEN": "${SNYK_TOKEN}"},
    }


def _extract_dependencies(pkgs: list, purl_type: str) -> list[dict]:
    """Extract name/version/purl_type from --print-graph pkg list."""
    if not pkgs:
        return []

    packages = []
    seen = set()

    for pkg in pkgs:
        info = pkg.get("info") or {}
        name = str(info.get("name", "")).strip()
        version_val = info.get("version", "")
        version = str(version_val).strip()
        if not name:
            continue
        key = (name, version, purl_type)
        if key in seen:
            continue
        seen.add(key)
        packages.append({"name": name, "version": version, "purl_type": purl_type})

    return packages


def _get_purl_type_from_pm(pm_name: str) -> str:
    """Map Snyk package manager name to purl_type."""
    name = pm_name.strip()
    return PACKAGE_MANAGER_PURL_TYPE_MAP.get(name, PURL_TYPE_DEFAULT)


def _parse_snyk_output(raw_output: str) -> list[dict]:
    """Parse Snyk's output.

    Handles:
    - Error JSON object ({"ok": false, ...}) -> []
    - DepGraph mixed text+JSON -> parse 'pkgs' and add purl_type = pkgManager.name
    """
    decoder = json.JSONDecoder()
    s = raw_output.strip()

    # Find the first "{" and decode from there (handles mixed text+json).
    start = s.find("{")
    if start == -1:
        return []
    try:
        first_obj, _ = decoder.raw_decode(s[start:])
    except (json.JSONDecodeError, ValueError):
        return []

    if not isinstance(first_obj, dict):
        return []

    # Error object
    if first_obj.get("ok") is False:
        return []

    # DepGraph format
    if "pkgs" in first_obj and isinstance(first_obj["pkgs"], list):
        pkg_manager = first_obj.get("pkgManager") or {}
        pm_name = str(pkg_manager.get("name", ""))
        purl_type = _get_purl_type_from_pm(pm_name)
        return _extract_dependencies(first_obj["pkgs"], purl_type)

    else:
        return []


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
