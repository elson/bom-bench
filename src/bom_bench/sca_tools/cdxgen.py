"""cdxgen SCA tool plugin for bom-bench.

cdxgen (CycloneDX Generator) is a tool for generating CycloneDX SBOMs
from various package managers and ecosystems.

Installation:
    npm install -g @cyclonedx/cdxgen

Usage:
    This plugin is automatically loaded by bom-bench. Once cdxgen is
    installed, it will be available as an SCA tool:

        bom-bench benchmark --pm uv --tools cdxgen

See: https://github.com/CycloneDX/cdxgen
"""

import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from bom_bench import hookimpl


def _get_cdxgen_version() -> Optional[str]:
    """Get cdxgen version number.

    Extracts the version number from the first line of cdxgen --version output.
    Removes ANSI escape codes (bold formatting, etc).
    Example: "CycloneDX Generator 11.11.0" -> "11.11.0"
    """
    try:
        result = subprocess.run(
            ["cdxgen", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # Get first line (contains version)
            first_line = result.stdout.strip().split('\n')[0]
            # Remove ANSI escape codes (e.g., \033[1m for bold)
            first_line = re.sub(r'\033\[[0-9;]*m', '', first_line)
            # Extract version number (last space-separated token)
            # "CycloneDX Generator 11.11.0" -> "11.11.0"
            parts = first_line.split()
            if parts:
                return parts[-1]
    except Exception:
        pass
    return None


@hookimpl
def register_sca_tools() -> dict:
    """Register cdxgen as an available SCA tool."""
    return {
        "name": "cdxgen",
        "version": _get_cdxgen_version(),
        "description": "CycloneDX Generator - creates SBOMs from package manifests",
        "supported_ecosystems": ["python", "javascript", "java", "go", "rust", "dotnet"],
        "homepage": "https://github.com/CycloneDX/cdxgen",
        "installed": shutil.which("cdxgen") is not None
    }


@hookimpl
def scan_project(
    tool_name: str,
    project_dir: Path,
    output_path: Path,
    ecosystem: str,
    timeout: int = 120
) -> Optional[dict]:
    """Scan project using cdxgen to generate SBOM.

    Runs: cdxgen -o <output> <project_dir>

    Args:
        tool_name: Must be "cdxgen" for this plugin to handle it
        project_dir: Directory containing manifest/lock files
        output_path: Where to write the SBOM JSON
        ecosystem: Package ecosystem (used for logging, cdxgen auto-detects)
        timeout: Maximum execution time in seconds

    Returns:
        Dict with generation status and details
    """
    if tool_name != "cdxgen":
        return None

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    try:
        # Build cdxgen command
        cmd = [
            "cdxgen",
            "-o", str(output_path),
            str(project_dir)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        duration = time.time() - start_time

        # Check if SBOM was generated successfully
        if result.returncode == 0 and output_path.exists():
            # Validate JSON output
            try:
                with open(output_path) as f:
                    json.load(f)

                return {
                    "tool_name": "cdxgen",
                    "status": "success",
                    "sbom_path": str(output_path),
                    "duration_seconds": duration,
                    "exit_code": result.returncode
                }
            except json.JSONDecodeError as e:
                return {
                    "tool_name": "cdxgen",
                    "status": "parse_error",
                    "error_message": f"Invalid JSON output: {e}",
                    "duration_seconds": duration,
                    "exit_code": result.returncode
                }
        else:
            error_msg = result.stderr.strip() if result.stderr else f"Exit code: {result.returncode}"
            return {
                "tool_name": "cdxgen",
                "status": "tool_failed",
                "error_message": error_msg,
                "duration_seconds": duration,
                "exit_code": result.returncode
            }

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return {
            "tool_name": "cdxgen",
            "status": "timeout",
            "error_message": f"Timeout after {timeout} seconds",
            "duration_seconds": duration
        }

    except FileNotFoundError:
        return {
            "tool_name": "cdxgen",
            "status": "tool_not_found",
            "error_message": "cdxgen not found in PATH. Install with: npm install -g @cyclonedx/cdxgen"
        }

    except Exception as e:
        duration = time.time() - start_time
        return {
            "tool_name": "cdxgen",
            "status": "tool_failed",
            "error_message": str(e),
            "duration_seconds": duration
        }
