"""Tests for bom_bench module exports (plugin dependency injection)."""


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
