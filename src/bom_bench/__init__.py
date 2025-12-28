"""bom-bench: Generate and lock multiple package manager projects from test scenarios."""

import pluggy

from bom_bench.config import __version__

# Convenience export for plugins: from bom_bench import hookimpl
hookimpl = pluggy.HookimplMarker("bom_bench")

__all__ = ["__version__", "hookimpl"]
