"""Packse fixture set plugin.

Provides Python dependency resolution test scenarios from the packse project.
Fixtures are generated from packse scenarios by running `uv lock` and parsing
the resulting lock files.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import packse.fetch
import packse.inspect
import tomlkit

from bom_bench import hookimpl

if TYPE_CHECKING:
    from types import ModuleType

# Configuration constants
UV_VERSION = "0.5.11"
PYTHON_VERSION = "3.12"
PACKSE_INDEX_URL = "http://127.0.0.1:3141/simple-html"
LOCK_TIMEOUT_SECONDS = 120


def _generate_pyproject_toml(
    name: str,
    version: str,
    dependencies: list[str],
    requires_python: str | None = None,
    required_environments: list[str] | None = None,
) -> str:
    """Generate pyproject.toml content."""
    doc = tomlkit.document()

    project = tomlkit.table()
    project["name"] = name
    project["version"] = version
    project["dependencies"] = dependencies if dependencies else []

    if requires_python:
        project["requires-python"] = requires_python

    doc["project"] = project

    if required_environments:
        if "tool" not in doc:
            doc["tool"] = tomlkit.table()

        uv_table = tomlkit.table()
        uv_table["required-environments"] = required_environments
        doc["tool"]["uv"] = uv_table  # type: ignore[index]

    return tomlkit.dumps(doc)


def _parse_uv_lock(lock_file_path: Path) -> list[dict]:
    """Parse uv.lock file and extract resolved packages."""
    if not lock_file_path.exists():
        return []

    with open(lock_file_path, encoding="utf-8") as f:
        lock_data = tomlkit.load(f)

    packages = []
    for package in lock_data.get("package", []):
        source = package.get("source", {})
        if source.get("virtual") == ".":
            continue

        name = package.get("name")
        version = package.get("version")

        if name and version:
            packages.append({"name": name, "version": version})

    return packages


def _compute_cache_hash(data_dir: Path) -> str:
    """Compute hash of packse source data for cache invalidation."""
    hasher = hashlib.sha256()
    for f in sorted(data_dir.glob("**/*.toml")):
        hasher.update(f.read_bytes())
    return hasher.hexdigest()


def _load_cache_manifest(cache_dir: Path) -> dict | None:
    """Load cache manifest if it exists."""
    manifest_path = cache_dir / ".cache_manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text())
    return None


def _save_cache_manifest(cache_dir: Path, source_hash: str) -> None:
    """Save cache manifest."""
    manifest_path = cache_dir / ".cache_manifest.json"
    manifest_path.write_text(json.dumps({"source_hash": source_hash}))


def _generate_fixture(
    scenario: dict,
    output_dir: Path,
    bom_bench: ModuleType,
    timeout: int = LOCK_TIMEOUT_SECONDS,
) -> dict | None:
    """Generate a single fixture from a scenario.

    Returns fixture dict with files info, or None if generation fails.
    """
    logger = bom_bench.get_logger(__name__)
    name = scenario["name"]

    fixture_dir = output_dir / name
    fixture_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Generate pyproject.toml
        dependencies = [req["requirement"] for req in scenario["root"]["requires"]]
        requires_python = scenario["root"]["requires_python"]
        required_environments = scenario["resolver_options"]["required_environments"]

        content = _generate_pyproject_toml(
            name="project",
            version="0.1.0",
            dependencies=dependencies,
            requires_python=requires_python,
            required_environments=required_environments if required_environments else None,
        )

        manifest_path = fixture_dir / "pyproject.toml"
        manifest_path.write_text(content)

        # Run uv lock
        lock_file = fixture_dir / "uv.lock"
        satisfiable = False
        exit_code = 1
        stdout = ""
        stderr = ""

        try:
            proc = subprocess.run(
                ["uv", "lock", "--index-url", PACKSE_INDEX_URL],
                cwd=fixture_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            exit_code = proc.returncode
            stdout = proc.stdout
            stderr = proc.stderr
            satisfiable = exit_code == 0
        except subprocess.TimeoutExpired:
            stderr = f"Timeout after {timeout} seconds"
            logger.warning(f"Timeout generating fixture: {name}")
        except FileNotFoundError:
            stderr = "uv not found"
            logger.warning("uv not installed, cannot generate packse fixtures")
            return None

        # Generate meta.json
        meta_path = fixture_dir / "meta.json"
        bom_bench.generate_meta_file(meta_path, satisfiable, exit_code, stdout, stderr)

        # Generate expected SBOM if satisfiable
        sbom_path = fixture_dir / "expected.cdx.json" if satisfiable else None
        if satisfiable and lock_file.exists():
            packages = _parse_uv_lock(lock_file)
            sbom_path = fixture_dir / "expected.cdx.json"
            bom_bench.generate_sbom_file(name, sbom_path, packages)

        return {
            "name": name,
            "files": {
                "manifest": str(manifest_path),
                "lock_file": str(lock_file) if lock_file.exists() else None,
                "expected_sbom": str(sbom_path) if sbom_path and sbom_path.exists() else None,
                "meta": str(meta_path),
            },
            "satisfiable": satisfiable,
            "description": scenario.get("description"),
        }

    except Exception as e:
        logger.error(f"Error generating fixture {name}: {e}")
        return None


def _should_include_scenario(scenario: dict, exclude_patterns: list[str]) -> bool:
    """Check if scenario should be included based on filters."""
    name = scenario.get("name", "")

    # Check universal resolver option
    resolver_options = scenario.get("resolver_options", {})
    if not resolver_options.get("universal", False):
        return False

    # Check exclude patterns
    return all(pattern.lower() not in name.lower() for pattern in exclude_patterns)


def _generate_fixtures(
    bom_bench: ModuleType,
    data_dir: Path,
    cache_dir: Path,
    exclude_patterns: list[str] | None = None,
) -> list[dict]:
    """Generate all packse fixtures with caching."""
    logger = bom_bench.get_logger(__name__)
    exclude_patterns = exclude_patterns or ["example"]

    # Fetch packse data if needed
    if not data_dir.exists():
        logger.info(f"Fetching packse scenarios to {data_dir}")
        packse.fetch.fetch(dest=data_dir)

    # Check cache
    source_hash = _compute_cache_hash(data_dir)
    cache_manifest = _load_cache_manifest(cache_dir)

    if cache_manifest and cache_manifest.get("source_hash") == source_hash:
        logger.debug("Using cached packse fixtures")
        return _load_cached_fixtures(cache_dir)

    # Generate fixtures
    logger.info("Generating packse fixtures...")
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Load scenarios
    scenario_files = list(packse.inspect.find_scenario_files(data_dir))
    if not scenario_files:
        logger.warning("No packse scenario files found")
        return []

    template_vars = packse.inspect.variables_for_templates(scenario_files, no_hash=True)
    scenarios = template_vars.get("scenarios", [])

    # Filter and generate
    fixtures = []
    for scenario in scenarios:
        if not _should_include_scenario(scenario, exclude_patterns):
            continue

        fixture = _generate_fixture(scenario, cache_dir, bom_bench)
        if fixture:
            fixtures.append(fixture)
            logger.debug(f"Generated fixture: {fixture['name']}")

    # Save cache manifest
    _save_cache_manifest(cache_dir, source_hash)
    logger.info(f"Generated {len(fixtures)} packse fixtures")

    return fixtures


def _load_cached_fixtures(cache_dir: Path) -> list[dict]:
    """Load fixtures from cache directory."""
    fixtures = []

    for fixture_dir in sorted(cache_dir.iterdir()):
        if not fixture_dir.is_dir() or fixture_dir.name.startswith("."):
            continue

        meta_path = fixture_dir / "meta.json"
        if not meta_path.exists():
            continue

        meta = json.loads(meta_path.read_text())

        fixture = {
            "name": fixture_dir.name,
            "files": {
                "manifest": str(fixture_dir / "pyproject.toml"),
                "lock_file": str(fixture_dir / "uv.lock")
                if (fixture_dir / "uv.lock").exists()
                else None,
                "expected_sbom": str(fixture_dir / "expected.cdx.json")
                if (fixture_dir / "expected.cdx.json").exists()
                else None,
                "meta": str(meta_path),
            },
            "satisfiable": meta.get("satisfiable", False),
        }
        fixtures.append(fixture)

    return fixtures


@hookimpl
def register_fixture_sets(bom_bench: ModuleType) -> list[dict]:
    """Register the packse fixture set.

    Uses dependency injection - receives bom_bench module for helpers.
    """
    from bom_bench.config import DATA_DIR

    data_dir = DATA_DIR / "packse"
    cache_dir = DATA_DIR / "fixture_sets" / "packse"

    fixtures = _generate_fixtures(bom_bench, data_dir, cache_dir)

    return [
        {
            "name": "packse",
            "description": "Python dependency resolution test scenarios from packse",
            "ecosystem": "python",
            "environment": {
                "tools": [
                    {"name": "uv", "version": UV_VERSION},
                    {"name": "python", "version": PYTHON_VERSION},
                ],
                "env_vars": {},
                "registry_url": PACKSE_INDEX_URL,
            },
            "fixtures": fixtures,
        }
    ]
