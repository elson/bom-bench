"""npm fixture set plugin using arborist test data."""

import hashlib
import json
import subprocess
from pathlib import Path
from types import ModuleType

from bom_bench import hookimpl

from .arborist_parser import ResolvedPackage, parse_snapshot_file
from .fixture_mapper import build_fixture_mapping
from .test_runner import run_arborist_tests

NPM_CLI_TAG = "v10.9.2"
NPM_CLI_REPO = "https://github.com/npm/cli.git"
NODE_VERSION = "22"


@hookimpl
def register_fixture_sets(bom_bench: ModuleType, data_dir: Path) -> list[dict]:
    """Register npm fixture set from arborist test data."""
    logger = bom_bench.get_logger(__name__)

    npm_cli_dir = data_dir / "npm-cli"
    cache_dir = data_dir / "fixture_sets" / "npm"

    fixtures = _load_fixtures(bom_bench, logger, npm_cli_dir, cache_dir)

    return [
        {
            "name": "npm",
            "description": "npm arborist dependency resolution test scenarios",
            "ecosystem": "javascript",
            "environment": {
                "tools": [{"name": "node", "version": NODE_VERSION}],
                "env": {},
                "registry_url": None,
            },
            "fixtures": fixtures,
        }
    ]


def _load_fixtures(
    bom_bench: ModuleType,
    logger,
    npm_cli_dir: Path,
    cache_dir: Path,
) -> list[dict]:
    """Load all npm fixtures from arborist test data."""
    repo_path = _clone_npm_cli(logger, npm_cli_dir)

    cache_hash = _compute_source_hash(repo_path)
    if _is_cache_valid(cache_dir, cache_hash):
        logger.info("Using cached npm fixtures")
        return _load_cached_fixtures(cache_dir)

    # Run arborist tests with --save-fixture to generate test output directories
    logger.info("Running arborist tests to generate fixtures...")
    test_result = run_arborist_tests(repo_path)

    if not test_result.success:
        logger.warning(
            f"Test run completed with exit code {test_result.exit_code}. "
            f"Continuing with available fixtures..."
        )

    logger.info(f"Tests completed in {test_result.duration_seconds:.1f}s")

    # Build mapping from saved fixture directories to snapshot entries
    snapshot_path = repo_path / "workspaces/arborist/tap-snapshots/test/arborist/reify.js.test.cjs"
    snapshot_ground_truth = parse_snapshot_file(snapshot_path)

    fixture_mapping = build_fixture_mapping(snapshot_path, test_result.fixtures_dir)
    logger.info(f"Found {len(fixture_mapping)} saved fixture directories")

    # Process each saved fixture
    fixtures = []
    for _fixture_name, mapping_entry in sorted(fixture_mapping.items()):
        fixture = _process_saved_fixture(
            mapping_entry,
            snapshot_ground_truth,
            bom_bench,
            logger,
            cache_dir,
        )
        if fixture:
            fixtures.append(fixture)

    _save_cache_manifest(cache_dir, cache_hash)
    logger.info(f"Loaded {len(fixtures)} npm fixtures")
    return fixtures


def _clone_npm_cli(logger, npm_cli_dir: Path) -> Path:
    """Shallow clone npm/cli repo at specific tag."""
    if npm_cli_dir.exists():
        result = subprocess.run(
            ["git", "describe", "--tags"],
            cwd=npm_cli_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and NPM_CLI_TAG in result.stdout:
            return npm_cli_dir
        import shutil

        shutil.rmtree(npm_cli_dir)

    logger.info(f"Cloning npm/cli at {NPM_CLI_TAG}...")
    npm_cli_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            NPM_CLI_TAG,
            NPM_CLI_REPO,
            str(npm_cli_dir),
        ],
        check=True,
    )
    return npm_cli_dir


def _process_saved_fixture(
    mapping_entry,
    snapshot_ground_truth: dict[str, list[ResolvedPackage]],
    bom_bench: ModuleType,
    logger,
    cache_dir: Path,
) -> dict | None:
    """Process a saved fixture directory from test output.

    Args:
        mapping_entry: FixtureMappingEntry with fixture info
        snapshot_ground_truth: Parsed snapshot file with expected packages
        bom_bench: bom_bench module for SBOM generation
        logger: Logger instance
        cache_dir: Directory to cache processed fixtures

    Returns:
        Fixture dict or None if skipped
    """
    fixture_name = mapping_entry.fixture_name
    saved_dir = mapping_entry.saved_dir
    test_name = mapping_entry.test_name

    # Skip malformed/unsatisfiable fixtures
    if any(x in fixture_name for x in ["malformed", "-fail", "unresolvable"]):
        return None

    # Check if saved directory has required files
    package_json_path = saved_dir / "package.json"
    if not package_json_path.exists():
        logger.debug(f"Skipping {fixture_name}: no package.json in saved directory")
        return None

    # Read package.json
    try:
        package_json = json.loads(package_json_path.read_text())
    except json.JSONDecodeError:
        logger.debug(f"Skipping {fixture_name}: invalid package.json")
        return None

    # Check for lock file
    package_lock_path = saved_dir / "package-lock.json"
    package_lock = None
    if package_lock_path.exists():
        try:
            package_lock = json.loads(package_lock_path.read_text())
        except json.JSONDecodeError:
            logger.debug(f"Skipping {fixture_name}: invalid package-lock.json")
            return None

    # Determine ground truth source
    if package_lock:
        # Use lock file as ground truth
        packages = _extract_packages_from_lock(package_lock)
        if not packages:
            logger.debug(f"Skipping {fixture_name}: no packages in lock file")
            return None
        ground_truth_source = "lock file"
    else:
        # Use tap snapshot for fixtures without lock files
        if test_name not in snapshot_ground_truth:
            logger.debug(f"Skipping {fixture_name}: no tap snapshot ground truth")
            return None

        packages = snapshot_ground_truth[test_name]
        if not packages:
            logger.debug(f"Skipping {fixture_name}: empty package list in snapshot")
            return None
        ground_truth_source = "tap snapshot"

    logger.debug(
        f"Generated fixture: {fixture_name} with {len(packages)} packages (from {ground_truth_source})"
    )

    # Copy files to cache
    fixture_dir = cache_dir / fixture_name
    fixture_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = fixture_dir / "package.json"
    manifest_path.write_text(json.dumps(package_json, indent=2))

    lock_path = None
    if package_lock:
        lock_path = fixture_dir / "package-lock.json"
        lock_path.write_text(json.dumps(package_lock, indent=2))

    # Generate expected SBOM
    sbom_path = fixture_dir / "expected.cdx.json"
    _generate_expected_sbom(bom_bench, fixture_name, packages, sbom_path)

    meta_path = fixture_dir / "meta.json"
    meta_path.write_text(json.dumps({"satisfiable": True}, indent=2))

    files = {
        "manifest": str(manifest_path),
        "expected_sbom": str(sbom_path),
        "meta": str(meta_path),
    }
    if lock_path:
        files["lock_file"] = str(lock_path)

    return {
        "name": fixture_name,
        "satisfiable": True,
        "files": files,
    }


def _extract_packages_from_lock(lock_data: dict) -> list[ResolvedPackage]:
    """Extract resolved packages from package-lock.json.

    Args:
        lock_data: Parsed package-lock.json content

    Returns:
        List of ResolvedPackage objects from the lock file
    """
    packages = []
    dependencies = lock_data.get("dependencies", {})

    for name, info in dependencies.items():
        version = info.get("version")
        resolved = info.get("resolved")

        # Only include packages with registry URLs (skip file: and link: dependencies)
        if version and resolved and "registry.npmjs.org" in resolved:
            packages.append(ResolvedPackage(name=name, version=version, resolved=resolved))

    return packages


def _generate_expected_sbom(
    bom_bench: ModuleType,
    fixture_name: str,
    packages: list[ResolvedPackage],
    sbom_path: Path,
) -> None:
    """Generate expected CycloneDX SBOM from ArboristNode resolved packages."""
    # Deduplicate packages by (name, version)
    seen = set()
    unique_packages = []
    for pkg in packages:
        key = (pkg.name, pkg.version)
        if key not in seen:
            seen.add(key)
            unique_packages.append({"name": pkg.name, "version": pkg.version, "purl_type": "npm"})

    bom_bench.generate_sbom_file(
        fixture_name,
        sbom_path,
        unique_packages,
    )


def _compute_source_hash(repo_path: Path) -> str:
    """Compute hash of source files for cache invalidation."""
    hasher = hashlib.sha256()

    # Hash test file (generates fixtures)
    test_file = repo_path / "workspaces/arborist/test/arborist/reify.js"
    if test_file.exists():
        hasher.update(test_file.read_bytes())

    # Hash snapshot file (expected output)
    snapshot = repo_path / "workspaces/arborist/tap-snapshots/test/arborist/reify.js.test.cjs"
    if snapshot.exists():
        hasher.update(snapshot.read_bytes())

    return hasher.hexdigest()[:16]


def _is_cache_valid(cache_dir: Path, current_hash: str) -> bool:
    """Check if cache is valid based on hash."""
    manifest = cache_dir / ".cache_manifest.json"
    if not manifest.exists():
        return False
    try:
        data = json.loads(manifest.read_text())
        return data.get("hash") == current_hash
    except Exception:
        return False


def _save_cache_manifest(cache_dir: Path, hash_value: str) -> None:
    """Save cache manifest with hash."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest = cache_dir / ".cache_manifest.json"
    manifest.write_text(json.dumps({"hash": hash_value}, indent=2))


def _load_cached_fixtures(cache_dir: Path) -> list[dict]:
    """Load fixtures from cache."""
    fixtures = []
    for fixture_dir in sorted(cache_dir.iterdir()):
        if not fixture_dir.is_dir() or fixture_dir.name.startswith("."):
            continue
        meta_path = fixture_dir / "meta.json"
        if not meta_path.exists():
            continue

        files = {
            "manifest": str(fixture_dir / "package.json"),
            "expected_sbom": str(fixture_dir / "expected.cdx.json"),
            "meta": str(meta_path),
        }

        lock_path = fixture_dir / "package-lock.json"
        if lock_path.exists():
            files["lock_file"] = str(lock_path)

        fixtures.append(
            {
                "name": fixture_dir.name,
                "satisfiable": True,
                "files": files,
            }
        )
    return fixtures
