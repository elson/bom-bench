# Plan: npm Fixture Set Plugin for bom-bench

## Overview

Create a new `npm` FixtureSet plugin that uses npm CLI's arborist test fixtures as the source of ground truth for benchmarking SCA tools against JavaScript/npm ecosystem dependencies.

## Key Design Decisions

### 1. Consistent Ground Truth Source

**Always use ArboristNode tap snapshot data for ground truth**, regardless of whether the fixture has an embedded lockfile.

**Rationale:**
- ArboristNode snapshots represent what npm's arborist *actually resolved* during tests
- Embedded lockfiles may differ from what arborist resolves (they're inputs, not outputs)
- Using a single source ensures consistency across all fixtures
- Fixtures without matching tap snapshot entries are skipped (no ground truth = no fixture)

### 2. Dependency Injection - Fully Encapsulated Plugin

**DO NOT import modules from `bom_bench`**. The plugin receives everything it needs via the `bom_bench` parameter and `data_dir` argument:

```python
@hookimpl
def register_fixture_sets(bom_bench: ModuleType, data_dir: Path) -> list[dict]:
    # Use bom_bench.get_logger(), bom_bench.generate_sbom_file(), etc.
    # Use data_dir for cache paths
```

### 3. No Separate Parser Modules

All npm-specific code lives within the plugin itself. The plugin can be structured as a module (directory) for maintainability:

```
src/bom_bench/fixtures/
├── __init__.py
├── packse.py
└── npm/
    ├── __init__.py      # Main plugin with hookimpl
    ├── js_parser.py     # tree-sitter JS parsing (internal)
    └── arborist_parser.py  # ArboristNode parsing (internal)
```

### 4. No Lock File Generation

**DO NOT create lock files for fixtures that don't have them.** Fixtures without lockfiles are intentionally designed that way - creating them would artificially influence SCA tool analysis.

- Fixtures WITH embedded lockfile: Use it as-is
- Fixtures WITHOUT lockfile: `lock_file` field is `None` or omitted

---

## Data Sources (from npm CLI repo at specific commit)

1. **Fixture definitions**: `workspaces/arborist/test/fixtures/reify-cases/*.js`
2. **Ground truth (ALWAYS)**: `workspaces/arborist/tap-snapshots/test/arborist/reify.js.test.cjs`
3. **Test correlation**: `workspaces/arborist/test/arborist/reify.js`

---

## Implementation Plan

### Step 1: Update Hook Specification

**File**: `src/bom_bench/plugins/hookspecs.py`

Add `data_dir` parameter to the hook spec:

```python
@hookspec
def register_fixture_sets(bom_bench: ModuleType, data_dir: Path) -> list[dict]:
    """Register fixture sets for benchmarking."""
```

### Step 2: Update Plugin Initialization

**File**: `src/bom_bench/fixtures/loader.py` (or wherever plugins are called)

Pass `data_dir` when calling the hook:

```python
results = pm.hook.register_fixture_sets(bom_bench=bom_bench_module, data_dir=DATA_DIR)
```

### Step 3: Update packse Plugin

**File**: `src/bom_bench/fixtures/packse.py`

Update signature to accept `data_dir`:

```python
@hookimpl
def register_fixture_sets(bom_bench: ModuleType, data_dir: Path) -> list[dict]:
    cache_dir = data_dir / "fixture_sets" / "packse"
    # ... rest of implementation uses cache_dir instead of hardcoded DATA_DIR
```

### Step 4: Add Dependencies

**File**: `pyproject.toml`

```toml
[project.dependencies]
tree-sitter = ">=0.23.0"
tree-sitter-javascript = ">=0.23.0"
```

### Step 5: Create npm Plugin Module

**Directory structure:**
```
src/bom_bench/fixtures/npm/
├── __init__.py          # Main plugin, exports register_fixture_sets
├── js_parser.py         # tree-sitter JS parsing
└── arborist_parser.py   # ArboristNode snapshot parsing
```

### Step 6: Implement tree-sitter JS Parser

**File**: `src/bom_bench/fixtures/npm/js_parser.py`

```python
"""Tree-sitter based parser for npm reify-case JS files."""

from pathlib import Path

import tree_sitter_javascript as ts_js
from tree_sitter import Language, Parser, Node

JS_LANGUAGE = Language(ts_js.language())


def create_js_parser() -> Parser:
    """Create a tree-sitter parser for JavaScript."""
    parser = Parser(JS_LANGUAGE)
    return parser


def get_node_text(node: Node, source: bytes) -> str:
    """Extract text content from a tree-sitter node."""
    return source[node.start_byte:node.end_byte].decode('utf-8')


def parse_reify_case(js_path: Path) -> dict | None:
    """Parse a reify-case JS file to extract package.json and package-lock.json.

    Returns:
        {
            "name": "fixture-name",
            "package_json": {...},
            "package_lock": {...} | None,  # May be present, used as fixture input
        }
    """
    parser = create_js_parser()
    source = js_path.read_bytes()
    tree = parser.parse(source)

    testdir_obj = _find_testdir_object(tree.root_node, source)
    if not testdir_obj:
        return None

    result = {
        "name": js_path.stem,
        "package_json": None,
        "package_lock": None,
    }

    for key, value in testdir_obj.items():
        if key == "package.json" and isinstance(value, dict):
            result["package_json"] = value
        elif key == "package-lock.json" and isinstance(value, dict):
            result["package_lock"] = value

    return result if result["package_json"] else None


def _find_testdir_object(node: Node, source: bytes) -> dict | None:
    """Find the object passed to t.testdir() call."""
    if node.type == 'call_expression':
        callee = node.child_by_field_name('function')
        if callee:
            callee_text = get_node_text(callee, source)
            if 'testdir' in callee_text:
                args = node.child_by_field_name('arguments')
                if args:
                    for child in args.children:
                        if child.type == 'object':
                            return _parse_testdir_entries(child, source)

    for child in node.children:
        result = _find_testdir_object(child, source)
        if result:
            return result
    return None


def _parse_testdir_entries(node: Node, source: bytes) -> dict:
    """Parse testdir object, handling JSON.stringify() calls for values."""
    result = {}
    for child in node.children:
        if child.type == 'pair':
            key_node = child.child_by_field_name('key')
            value_node = child.child_by_field_name('value')
            if key_node and value_node:
                key = get_node_text(key_node, source).strip('"')

                if value_node.type == 'call_expression':
                    value = _find_json_stringify_arg(value_node, source)
                else:
                    value = _parse_value(value_node, source)

                result[key] = value
    return result


def _find_json_stringify_arg(node: Node, source: bytes) -> dict | None:
    """Find and parse the argument to JSON.stringify() call."""
    if node.type == 'call_expression':
        callee = node.child_by_field_name('function')
        if callee and get_node_text(callee, source) == 'JSON.stringify':
            args = node.child_by_field_name('arguments')
            if args and args.child_count > 1:
                obj_node = args.child(1)
                if obj_node and obj_node.type == 'object':
                    return _parse_object_literal(obj_node, source)

    for child in node.children:
        result = _find_json_stringify_arg(child, source)
        if result:
            return result
    return None


def _parse_object_literal(node: Node, source: bytes) -> dict:
    """Parse a JS object literal into a Python dict."""
    result = {}
    for child in node.children:
        if child.type == 'pair':
            key_node = child.child_by_field_name('key')
            value_node = child.child_by_field_name('value')
            if key_node and value_node:
                key = get_node_text(key_node, source).strip('"')
                value = _parse_value(value_node, source)
                result[key] = value
    return result


def _parse_value(node: Node, source: bytes):
    """Parse a JS value node into Python equivalent."""
    if node.type == 'string':
        return get_node_text(node, source)[1:-1]  # Remove quotes
    elif node.type == 'number':
        text = get_node_text(node, source)
        return float(text) if '.' in text else int(text)
    elif node.type == 'true':
        return True
    elif node.type == 'false':
        return False
    elif node.type == 'null':
        return None
    elif node.type == 'object':
        return _parse_object_literal(node, source)
    elif node.type == 'array':
        return [_parse_value(c, source) for c in node.children if c.type not in ('[', ']', ',')]
    elif node.type == 'call_expression':
        return _find_json_stringify_arg(node, source)
    return None


def parse_fixture_test_mapping(test_file: Path) -> dict[str, str]:
    """Parse reify.js to map fixture names to test names.

    Correlation:
    - Fixture file: `reify-cases/testing-peer-deps.js`
    - Test in reify.js: `t.test('testing-peer-deps package', ... fixture(t, 'testing-peer-deps') ...)`
    - Snapshot key: `test/arborist/reify.js TAP testing-peer-deps package > expect resolving Promise 1`

    Returns: {"testing-peer-deps": "testing-peer-deps package", ...}
    """
    parser = create_js_parser()
    source = test_file.read_bytes()
    tree = parser.parse(source)
    mapping = {}
    _find_fixture_calls(tree.root_node, source, mapping)
    return mapping


def _find_fixture_calls(node: Node, source: bytes, mapping: dict) -> None:
    """Recursively find fixture() calls within t.test() calls.

    Looks for patterns like:
    t.test('test name', async t => {
        ...
        fixture(t, 'fixture-name')
        ...
    })
    """
    # Find t.test() calls
    if node.type == 'call_expression':
        callee = node.child_by_field_name('function')
        if callee and 't.test' in get_node_text(callee, source):
            args = node.child_by_field_name('arguments')
            if args and args.child_count >= 2:
                # First arg is test name
                test_name_node = args.child(1)
                if test_name_node and test_name_node.type == 'string':
                    test_name = get_node_text(test_name_node, source)[1:-1]

                    # Search for fixture() calls in the callback body
                    for child in node.children:
                        fixture_name = _find_fixture_name_in_node(child, source)
                        if fixture_name:
                            mapping[fixture_name] = test_name
                            break

    for child in node.children:
        _find_fixture_calls(child, source, mapping)


def _find_fixture_name_in_node(node: Node, source: bytes) -> str | None:
    """Find fixture(t, 'name') call and extract fixture name."""
    if node.type == 'call_expression':
        callee = node.child_by_field_name('function')
        if callee and get_node_text(callee, source) == 'fixture':
            args = node.child_by_field_name('arguments')
            if args and args.child_count >= 3:
                # Second arg (index 2) is fixture name
                name_node = args.child(2)
                if name_node and name_node.type == 'string':
                    return get_node_text(name_node, source)[1:-1]

    for child in node.children:
        result = _find_fixture_name_in_node(child, source)
        if result:
            return result
    return None
```

### Step 7: Implement ArboristNode Parser

**File**: `src/bom_bench/fixtures/npm/arborist_parser.py`

```python
"""Parser for ArboristNode debug output in tap snapshots."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ResolvedPackage:
    """A resolved npm package from ArboristNode output."""
    name: str
    version: str
    resolved: str
    integrity: str | None = None


def parse_snapshot_file(snapshot_path: Path) -> dict[str, list[ResolvedPackage]]:
    """Parse tap-snapshot file to extract resolved packages per test.

    Returns: {"test-name": [ResolvedPackage(...), ...], ...}
    """
    content = snapshot_path.read_text()
    results = {}

    exports = _split_exports(content)

    for export_key, export_value in exports.items():
        if "expect resolving Promise" not in export_key:
            continue

        test_name = _extract_test_name(export_key)
        if not test_name:
            continue

        packages = _parse_arborist_content(export_value)
        if packages:
            results[test_name] = packages

    return results


def _split_exports(content: str) -> dict[str, str]:
    """Split snapshot file into individual exports."""
    exports = {}
    lines = content.split('\n')
    current_key = None
    current_value: list[str] = []
    in_template = False

    for line in lines:
        if line.startswith('exports[`'):
            if current_key and current_value:
                exports[current_key] = '\n'.join(current_value)

            key_end = line.find('`]')
            if key_end > 0:
                current_key = line[9:key_end]
                current_value = []
                in_template = True
        elif in_template:
            if line == '`':
                in_template = False
            else:
                current_value.append(line)

    if current_key and current_value:
        exports[current_key] = '\n'.join(current_value)

    return exports


def _extract_test_name(export_key: str) -> str | None:
    """Extract test name from export key.

    Example: "test/arborist/reify.js TAP testing-peer-deps package > expect resolving Promise 1"
    Returns: "testing-peer-deps package"
    """
    prefix = "test/arborist/reify.js TAP "
    suffix_marker = " > "

    if not export_key.startswith(prefix):
        return None

    rest = export_key[len(prefix):]
    suffix_idx = rest.find(suffix_marker)
    if suffix_idx < 0:
        return None

    return rest[:suffix_idx]


def _parse_arborist_content(content: str) -> list[ResolvedPackage]:
    """Parse ArboristNode debug format to extract resolved packages.

    ArboristNode format is consistent enough for line-based parsing:
    - "name": "package-name",
    - "version": "1.2.3",
    - "resolved": "https://registry.npmjs.org/..."
    """
    packages = []
    current: dict[str, str] = {}

    for line in content.split('\n'):
        line = line.strip()

        if '"name":' in line:
            current['name'] = _extract_string_value(line) or ''
        elif '"version":' in line:
            current['version'] = _extract_string_value(line) or ''
        elif '"resolved":' in line:
            resolved = _extract_string_value(line)
            if resolved and 'registry.npmjs.org' in resolved:
                current['resolved'] = resolved
                if current.get('name') and current.get('version'):
                    packages.append(ResolvedPackage(
                        name=current['name'],
                        version=current['version'],
                        resolved=current['resolved'],
                    ))
                current = {}
        elif line.startswith('}') or 'ArboristNode' in line:
            current = {}

    return packages


def _extract_string_value(line: str) -> str | None:
    """Extract string value from a line like: "key": "value","""
    colon_pos = line.find(':"')
    if colon_pos < 0:
        return None
    start = line.find('"', colon_pos + 1)
    if start < 0:
        return None
    end = line.find('"', start + 1)
    if end < 0:
        return None
    return line[start + 1:end]
```

### Step 8: Create Main npm Plugin

**File**: `src/bom_bench/fixtures/npm/__init__.py`

```python
"""npm fixture set plugin using arborist test data."""

from pathlib import Path
from types import ModuleType
import json
import subprocess
import hashlib

from bom_bench import hookimpl

from .js_parser import parse_reify_case, parse_fixture_test_mapping
from .arborist_parser import parse_snapshot_file, ResolvedPackage

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

    return [{
        "name": "npm",
        "description": "npm arborist dependency resolution test scenarios",
        "ecosystem": "javascript",
        "environment": {
            "tools": [{"name": "node", "version": NODE_VERSION}],
            "env": {},
            "registry_url": None,
        },
        "fixtures": fixtures,
    }]


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

    # Parse tap snapshot for ground truth (ALWAYS used for expected SBOM)
    snapshot_path = repo_path / "workspaces/arborist/tap-snapshots/test/arborist/reify.js.test.cjs"
    snapshot_ground_truth = parse_snapshot_file(snapshot_path)

    # Parse reify.js to map fixture names to test names
    test_file = repo_path / "workspaces/arborist/test/arborist/reify.js"
    fixture_to_test = parse_fixture_test_mapping(test_file)

    reify_cases_dir = repo_path / "workspaces/arborist/test/fixtures/reify-cases"
    fixtures = []

    for case_file in sorted(reify_cases_dir.glob("*.js")):
        fixture = _process_fixture(
            case_file, fixture_to_test, snapshot_ground_truth,
            bom_bench, logger, cache_dir,
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
            cwd=npm_cli_dir, capture_output=True, text=True,
        )
        if result.returncode == 0 and NPM_CLI_TAG in result.stdout:
            return npm_cli_dir
        import shutil
        shutil.rmtree(npm_cli_dir)

    logger.info(f"Cloning npm/cli at {NPM_CLI_TAG}...")
    npm_cli_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "git", "clone", "--depth", "1", "--branch", NPM_CLI_TAG,
        NPM_CLI_REPO, str(npm_cli_dir),
    ], check=True)
    return npm_cli_dir


def _process_fixture(
    case_file: Path,
    fixture_to_test: dict[str, str],
    snapshot_ground_truth: dict[str, list[ResolvedPackage]],
    bom_bench: ModuleType,
    logger,
    cache_dir: Path,
) -> dict | None:
    """Process a single reify-case fixture.

    IMPORTANT: Ground truth ALWAYS comes from ArboristNode tap data.
    Fixtures without matching tap snapshot entries are skipped.

    DO NOT generate lock files - fixtures without lockfiles are intentional.
    """
    fixture_name = case_file.stem

    # Skip error test cases
    if any(x in fixture_name for x in ['malformed', '-fail', 'unresolvable']):
        return None

    # Parse fixture JS file
    parsed = parse_reify_case(case_file)
    if not parsed or not parsed['package_json']:
        logger.debug(f"Skipping {fixture_name}: could not parse")
        return None

    # MUST have tap snapshot data for ground truth
    test_name = fixture_to_test.get(fixture_name)
    if not test_name or test_name not in snapshot_ground_truth:
        logger.debug(f"Skipping {fixture_name}: no tap snapshot ground truth")
        return None

    packages = snapshot_ground_truth[test_name]
    if not packages:
        logger.debug(f"Skipping {fixture_name}: empty package list in snapshot")
        return None

    fixture_dir = cache_dir / fixture_name
    fixture_dir.mkdir(parents=True, exist_ok=True)

    # Write package.json
    manifest_path = fixture_dir / "package.json"
    manifest_path.write_text(json.dumps(parsed['package_json'], indent=2))

    # Write package-lock.json ONLY if embedded in fixture
    # DO NOT generate lockfiles - fixtures without them are intentional
    lock_path: Path | None = None
    if parsed['package_lock']:
        lock_path = fixture_dir / "package-lock.json"
        lock_path.write_text(json.dumps(parsed['package_lock'], indent=2))

    # Generate expected SBOM from ArboristNode tap data (ALWAYS)
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
    pkg_list = [{"name": pkg.name, "version": pkg.version} for pkg in packages]
    bom_bench.generate_sbom_file(
        name=fixture_name,
        sbom_path=sbom_path,
        packages=pkg_list,
        purl_type="npm",
    )


def _compute_source_hash(repo_path: Path) -> str:
    """Compute hash of source files for cache invalidation."""
    hasher = hashlib.sha256()
    reify_cases = repo_path / "workspaces/arborist/test/fixtures/reify-cases"
    for f in sorted(reify_cases.glob('*.js')):
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
        return data.get('hash') == current_hash
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
        if not fixture_dir.is_dir() or fixture_dir.name.startswith('.'):
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

        fixtures.append({
            "name": fixture_dir.name,
            "satisfiable": True,
            "files": files,
        })
    return fixtures
```

### Step 9: Register Plugin

**File**: `src/bom_bench/plugins/__init__.py`

Add to `DEFAULT_PLUGINS`:
```python
DEFAULT_PLUGINS = (
    # ... existing plugins
    "bom_bench.fixtures.npm",
)
```

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `pyproject.toml` | Modify | Add tree-sitter dependencies |
| `src/bom_bench/plugins/hookspecs.py` | Modify | Add `data_dir` parameter to hook spec |
| `src/bom_bench/fixtures/loader.py` | Modify | Pass `data_dir` when calling hook |
| `src/bom_bench/fixtures/packse.py` | Modify | Accept `data_dir` parameter |
| `src/bom_bench/fixtures/npm/__init__.py` | Create | Main plugin |
| `src/bom_bench/fixtures/npm/js_parser.py` | Create | Tree-sitter JS parser (internal) |
| `src/bom_bench/fixtures/npm/arborist_parser.py` | Create | ArboristNode parser (internal) |
| `src/bom_bench/plugins/__init__.py` | Modify | Register plugin |
| `tests/unit/test_npm_plugin.py` | Create | Unit tests for plugin |

---

## Fixture Filtering Criteria

**Include:**
- Fixtures with parseable package.json
- Fixtures with matching tap snapshot entry (REQUIRED for ground truth)
- Fixtures with dependencies from registry.npmjs.org

**Exclude:**
- `malformed-json`, `*-fail`, `*-unresolvable` (error test cases)
- Fixtures without tap snapshot ground truth
- Fixtures with empty resolved package list

---

## Edge Cases

1. **Scoped packages**: `@scope/name` → `pkg:npm/%40scope/name@version`
2. **Nested dependencies**: `node_modules/a/node_modules/b` - extract innermost name
3. **Fixtures without lockfiles**: Keep `lock_file` field absent (DO NOT generate)
4. **Peer/dev/optional deps**: Include all resolved dependencies from ArboristNode

---

## Verification

```bash
# Unit tests
uv run pytest tests/unit/test_npm_plugin.py -xvs

# Integration tests
uv run bom-bench list-fixtures  # Should show npm fixtures
uv run bom-bench benchmark --fixture-sets npm --tools cdxgen

# Coverage
make check  # Full test suite with coverage
```

---

## Implementation Order

1. Update hook spec to add `data_dir` parameter
2. Update plugin loader to pass `data_dir`
3. Update packse plugin to accept `data_dir`
4. Add tree-sitter dependencies to `pyproject.toml`
5. Create `src/bom_bench/fixtures/npm/` module
6. Implement `js_parser.py` with tree-sitter
7. Implement `arborist_parser.py` for snapshot parsing
8. Create main plugin in `__init__.py`
9. Register in `plugins/__init__.py`
10. Write unit tests
11. Integration testing with bom-bench CLI
12. Ensure 100% coverage

---

## New Dependencies

```toml
tree-sitter = ">=0.23.0"
tree-sitter-javascript = ">=0.23.0"
```
