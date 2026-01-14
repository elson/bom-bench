"""npm fixture set plugin using arborist test data."""

import hashlib
import json
import subprocess
from pathlib import Path
from types import ModuleType

from bom_bench import hookimpl

from .arborist_parser import ResolvedPackage, parse_snapshot_file
from .js_parser import parse_fixture_test_mapping, parse_reify_case

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

    snapshot_path = repo_path / "workspaces/arborist/tap-snapshots/test/arborist/reify.js.test.cjs"
    snapshot_ground_truth = parse_snapshot_file(snapshot_path)

    test_file = repo_path / "workspaces/arborist/test/arborist/reify.js"
    fixture_to_test = parse_fixture_test_mapping(test_file)

    reify_cases_dir = repo_path / "workspaces/arborist/test/fixtures/reify-cases"
    fixtures = []

    for case_file in sorted(reify_cases_dir.glob("*.js")):
        fixture = _process_fixture(
            case_file,
            fixture_to_test,
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


def _process_fixture(
    case_file: Path,
    fixture_to_test: dict[str, str],
    snapshot_ground_truth: dict[str, list[ResolvedPackage]],
    bom_bench: ModuleType,
    logger,
    cache_dir: Path,
) -> dict | None:
    """Process a single reify-case fixture.

    Ground truth source depends on whether fixture has a lock file:
    - WITH lock file: Ground truth from lock file (what SCA tools should find)
    - WITHOUT lock file: Ground truth from tap snapshot (resolved dependencies)

    Fixtures without matching tap snapshot entries are skipped for validation.
    """
    fixture_name = case_file.stem

    if any(x in fixture_name for x in ["malformed", "-fail", "unresolvable"]):
        return None

    parsed = parse_reify_case(case_file)
    if not parsed or not parsed["package_json"]:
        logger.debug(f"Skipping {fixture_name}: could not parse")
        return None

    # Determine ground truth source
    if parsed["package_lock"]:
        # Use lock file as ground truth for SCA tool benchmarking
        packages = _extract_packages_from_lock(parsed["package_lock"])
        if not packages:
            logger.debug(f"Skipping {fixture_name}: no packages in lock file")
            return None
        ground_truth_source = "lock file"
    else:
        # Use tap snapshot for fixtures without lock files
        test_name = fixture_to_test.get(fixture_name)
        if not test_name or test_name not in snapshot_ground_truth:
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

    fixture_dir = cache_dir / fixture_name
    fixture_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = fixture_dir / "package.json"
    manifest_path.write_text(json.dumps(parsed["package_json"], indent=2))

    lock_path: Path | None = None
    if parsed["package_lock"]:
        lock_path = fixture_dir / "package-lock.json"
        lock_path.write_text(json.dumps(parsed["package_lock"], indent=2))

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
    reify_cases = repo_path / "workspaces/arborist/test/fixtures/reify-cases"
    for f in sorted(reify_cases.glob("*.js")):
        hasher.update(f.read_bytes())
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
