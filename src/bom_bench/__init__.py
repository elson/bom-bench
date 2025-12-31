"""bom-bench: Generate and lock multiple package manager projects from test scenarios."""

import pluggy

from bom_bench.config import __version__
from bom_bench.generators.sbom.cyclonedx import generate_meta_file, generate_sbom_file
from bom_bench.logging import get_logger

# Convenience export for plugins: from bom_bench import hookimpl
hookimpl = pluggy.HookimplMarker("bom_bench")

__all__ = [
    "__version__",
    "hookimpl",
    "generate_sbom_file",
    "generate_meta_file",
    "get_logger",
]
