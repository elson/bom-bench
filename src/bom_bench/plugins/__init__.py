"""Plugin system for bom-bench.

Uses Pluggy for plugin discovery and hook management.
Follows the Datasette pattern for plugin architecture.

Core plugin functions:
    from bom_bench.plugins import initialize_plugins, reset_plugins, get_plugins

For SCA tools, import from bom_bench.sca_tools:
    from bom_bench.sca_tools import (
        get_registered_tools,
        get_tool_info,
        get_tool_config,
    )
"""

import contextlib
import importlib

import pluggy

from bom_bench.logging import get_logger
from bom_bench.plugins.hookspecs import FixtureSetSpec, RendererSpec, SCAToolSpec

logger = get_logger(__name__)


# Default plugins bundled with bom-bench
# These are loaded automatically on initialization
DEFAULT_PLUGINS = (
    "bom_bench.sca_tools.cdxgen",
    "bom_bench.sca_tools.syft",
    "bom_bench.sca_tools.snyk",
    "bom_bench.fixtures.packse",
    "bom_bench.renderers.sca_tool_results_json",
    "bom_bench.renderers.sca_tool_results_csv",
    "bom_bench.renderers.sca_tool_summary_csv",
    "bom_bench.renderers.sca_tool_summary_toml",
    "bom_bench.renderers.benchmark_results_json",
    "bom_bench.renderers.benchmark_summary_csv",
    "bom_bench.renderers.benchmark_summary_toml",
)


# Create plugin manager with bom_bench namespace
pm = pluggy.PluginManager("bom_bench")
pm.add_hookspecs(FixtureSetSpec)
pm.add_hookspecs(SCAToolSpec)
pm.add_hookspecs(RendererSpec)

# Track initialization state
_initialized: bool = False


def _load_default_plugins() -> None:
    """Load plugins bundled with bom-bench."""
    for plugin_path in DEFAULT_PLUGINS:
        try:
            module = importlib.import_module(plugin_path)
            pm.register(module, name=plugin_path)
            logger.debug(f"Loaded plugin: {plugin_path}")
        except ImportError as e:
            logger.debug(f"Could not load plugin {plugin_path}: {e}")


def _load_external_plugins() -> None:
    """Discover and load external plugins via entry points."""
    try:
        num_loaded = pm.load_setuptools_entrypoints("bom_bench")
        if num_loaded > 0:
            logger.debug(f"Loaded {num_loaded} external plugin(s)")
    except Exception as e:
        logger.warning(f"Error loading external plugins: {e}")


def initialize_plugins() -> None:
    """Initialize the plugin system.

    Loads bundled plugins first, then discovers external plugins
    via entry points. Collects tool registrations from all plugins.

    This function is idempotent - calling it multiple times has no effect
    after the first call.
    """
    global _initialized

    if _initialized:
        return

    # Load default plugins
    _load_default_plugins()

    # Load external plugins via entry points
    _load_external_plugins()

    # Register via domain modules
    from bom_bench.sca_tools import _register_tools

    _register_tools(pm)

    _initialized = True

    # Get counts for logging
    from bom_bench.sca_tools import _registered_tools

    logger.debug(f"Plugin system initialized with {len(_registered_tools)} tool(s)")


def reset_plugins() -> None:
    """Reset the plugin system (mainly for testing).

    Clears all registered tools, unregisters all plugins, and marks
    the system as uninitialized. The next call to initialize_plugins()
    will re-initialize the system.
    """
    global _initialized

    # Unregister all plugins from the plugin manager
    for plugin in list(pm.get_plugins()):
        with contextlib.suppress(Exception):
            pm.unregister(plugin)

    # Reset domain module registries
    from bom_bench.sca_tools import _reset_tools

    _reset_tools()

    _initialized = False


def get_plugins() -> list[dict]:
    """Get information about loaded plugins.

    Returns:
        List of plugin info dictionaries with name, module, and hooks.
    """
    if not _initialized:
        initialize_plugins()

    plugins = []
    for plugin in pm.get_plugins():
        plugin_info = {
            "name": pm.get_name(plugin),
            "module": getattr(plugin, "__name__", str(plugin)),
        }
        plugins.append(plugin_info)

    return plugins


__all__ = [
    "pm",
    "DEFAULT_PLUGINS",
    "initialize_plugins",
    "reset_plugins",
    "get_plugins",
]
