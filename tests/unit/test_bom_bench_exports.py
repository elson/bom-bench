"""Tests for bom_bench module exports (plugin dependency injection)."""

import ast
from pathlib import Path


class TestPluginDecoupling:
    """Test that plugins only import hookimpl from bom_bench."""

    def test_uv_plugin_only_imports_hookimpl(self):
        """UV plugin should only import hookimpl from bom_bench (Datasette-style)."""
        uv_path = Path("src/bom_bench/package_managers/uv.py")
        source = uv_path.read_text()
        tree = ast.parse(source)

        bom_bench_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("bom_bench"):
                    for alias in node.names:
                        bom_bench_imports.append(f"from {node.module} import {alias.name}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("bom_bench"):
                        bom_bench_imports.append(f"import {alias.name}")

        assert bom_bench_imports == [
            "from bom_bench import hookimpl"
        ], f"UV plugin should only import hookimpl from bom_bench. Found: {bom_bench_imports}"


def test_hookimpl_is_exported():
    """hookimpl should be importable from bom_bench."""
    from bom_bench import hookimpl

    assert hookimpl is not None


def test_generate_sbom_file_is_exported():
    """generate_sbom_file should be importable from bom_bench for plugins."""
    from bom_bench import generate_sbom_file

    assert callable(generate_sbom_file)


def test_generate_meta_file_is_exported():
    """generate_meta_file should be importable from bom_bench for plugins."""
    from bom_bench import generate_meta_file

    assert callable(generate_meta_file)


def test_get_logger_is_exported():
    """get_logger should be importable from bom_bench for plugins."""
    from bom_bench import get_logger

    assert callable(get_logger)


def test_all_exports_in_dunder_all():
    """All plugin helpers should be listed in __all__."""
    import bom_bench

    expected_exports = {
        "__version__",
        "hookimpl",
        "generate_sbom_file",
        "generate_meta_file",
        "get_logger",
    }
    assert expected_exports.issubset(set(bom_bench.__all__))


class TestUVPluginInternals:
    """Test UV plugin internal structures are minimal."""

    def test_lock_result_has_minimal_fields(self):
        """_LockResult should only have fields that are actually used."""
        import dataclasses

        from bom_bench.package_managers.uv import _LockResult

        field_names = {f.name for f in dataclasses.fields(_LockResult)}
        # Only these 5 fields are actually used
        expected_fields = {"status", "exit_code", "stdout", "stderr", "error_message"}
        assert (
            field_names == expected_fields
        ), f"_LockResult has unused fields. Expected {expected_fields}, got {field_names}"

    def test_lock_status_has_minimal_values(self):
        """_LockStatus should only have values that are actually used."""
        from bom_bench.package_managers.uv import _LockStatus

        values = {s.value for s in _LockStatus}
        # ERROR is never used
        expected_values = {"success", "failed", "timeout"}
        assert (
            values == expected_values
        ), f"_LockStatus has unused values. Expected {expected_values}, got {values}"
