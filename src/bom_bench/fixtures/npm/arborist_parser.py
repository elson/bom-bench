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
    lines = content.split("\n")
    current_key = None
    current_value: list[str] = []
    in_template = False

    for line in lines:
        if line.startswith("exports[`") or line.startswith("exports['"):
            if current_key and current_value:
                exports[current_key] = "\n".join(current_value)

            quote_char = "`" if line.startswith("exports[`") else "'"
            key_end = line.find(f"{quote_char}]")
            if key_end > 0:
                current_key = line[9:key_end]
                current_value = []
                in_template = True
        elif in_template:
            if line == "`":
                in_template = False
            else:
                current_value.append(line)

    if current_key and current_value:
        exports[current_key] = "\n".join(current_value)

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

    rest = export_key[len(prefix) :]
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

    for line in content.split("\n"):
        line = line.strip()

        if '"name":' in line:
            current["name"] = _extract_string_value(line) or ""
        elif '"version":' in line:
            current["version"] = _extract_string_value(line) or ""
        elif '"resolved":' in line:
            resolved = _extract_string_value(line)
            if resolved and "registry.npmjs.org" in resolved:
                current["resolved"] = resolved
        elif line.startswith("}") or "ArboristNode" in line:
            # Check if we have a complete package before resetting
            if current.get("name") and current.get("version") and current.get("resolved"):
                packages.append(
                    ResolvedPackage(
                        name=current["name"],
                        version=current["version"],
                        resolved=current["resolved"],
                    )
                )
            current = {}

    return packages


def _extract_string_value(line: str) -> str | None:
    """Extract string value from a line like: "key": "value","""
    colon_pos = line.find('": "')
    if colon_pos < 0:
        return None
    start = colon_pos + 4
    end = line.find('"', start)
    if end < 0:
        return None
    return line[start:end]
