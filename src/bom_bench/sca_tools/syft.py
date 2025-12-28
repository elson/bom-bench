"""Syft SCA tool plugin for bom-bench.

Syft is an SBOM generation tool by Anchore that creates bill of materials
from container images and filesystems.

Installation:
    # macOS
    brew install syft

    # Linux/macOS (shell script)
    curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

    # Or download from: https://github.com/anchore/syft/releases

Usage:
    This plugin is automatically loaded by bom-bench. Once syft is
    installed, it will be available as an SCA tool:

        bom-bench benchmark --pm uv --tools syft

See: https://github.com/anchore/syft
"""

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from bom_bench import hookimpl


def _get_syft_version() -> Optional[str]:
    """Get Syft version number.

    Extracts version from `syft version` command output.
    Example output:
        Application:   syft
        Version:       1.39.0
        BuildDate:     2025-12-22T19:51:39Z
        ...

    Returns: "1.39.0"
    """
    try:
        result = subprocess.run(
            ["syft", "version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # Parse version from "Version: X.X.X" line
            for line in result.stdout.strip().split('\n'):
                if line.startswith('Version:'):
                    # Extract version number after "Version:"
                    version = line.split(':', 1)[1].strip()
                    return version
    except Exception:
        pass
    return None


@hookimpl
def register_sca_tools() -> dict:
    """Register Syft as an available SCA tool."""
    return {
        "name": "syft",
        "version": _get_syft_version(),
        "description": "Anchore Syft - SBOM generator for containers and filesystems",
        "supported_ecosystems": [
            "python",
            "javascript",
            "java",
            "go",
            "rust",
            "ruby",
            "php",
            "dotnet"
        ],
        "homepage": "https://github.com/anchore/syft",
        "installed": shutil.which("syft") is not None
    }


@hookimpl
def generate_sbom(
    tool_name: str,
    project_dir: Path,
    output_path: Path,
    ecosystem: str,
    timeout: int = 120
) -> Optional[dict]:
    """Generate SBOM using Syft.

    Runs: syft <project_dir> -o cyclonedx-json=<output_path>

    Args:
        tool_name: Must be "syft" for this plugin to handle it
        project_dir: Directory containing project files
        output_path: Where to write the SBOM JSON
        ecosystem: Package ecosystem (Syft auto-detects)
        timeout: Maximum execution time in seconds

    Returns:
        Dict with generation status and details
    """
    if tool_name != "syft":
        return None

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    try:
        # Build Syft command
        # Format: syft <target> -o cyclonedx-json=<output>
        cmd = [
            "syft",
            str(project_dir),
            "-o", f"cyclonedx-json={output_path}"
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
                    "tool_name": "syft",
                    "status": "success",
                    "sbom_path": str(output_path),
                    "duration_seconds": duration,
                    "exit_code": result.returncode
                }
            except json.JSONDecodeError as e:
                return {
                    "tool_name": "syft",
                    "status": "parse_error",
                    "error_message": f"Invalid JSON output: {e}",
                    "duration_seconds": duration,
                    "exit_code": result.returncode
                }
        else:
            error_msg = result.stderr.strip() if result.stderr else f"Exit code: {result.returncode}"
            return {
                "tool_name": "syft",
                "status": "tool_failed",
                "error_message": error_msg,
                "duration_seconds": duration,
                "exit_code": result.returncode
            }

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return {
            "tool_name": "syft",
            "status": "timeout",
            "error_message": f"Timeout after {timeout} seconds",
            "duration_seconds": duration
        }

    except FileNotFoundError:
        return {
            "tool_name": "syft",
            "status": "tool_not_found",
            "error_message": "syft not found in PATH. Install with: brew install syft"
        }

    except Exception as e:
        duration = time.time() - start_time
        return {
            "tool_name": "syft",
            "status": "tool_failed",
            "error_message": str(e),
            "duration_seconds": duration
        }
