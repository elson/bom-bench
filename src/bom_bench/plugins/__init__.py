"""Plugin system for bom-bench SCA tools.

Uses Pluggy for plugin discovery and hook management.
Follows the Datasette pattern for plugin architecture.

Usage:
    from bom_bench.plugins import (
        initialize_plugins,
        get_registered_tools,
        list_available_tools,
        check_tool_available,
        generate_sbom,
    )

    # Initialize plugins (called automatically on first use)
    initialize_plugins()

    # List available tools
    for tool_name in list_available_tools():
        print(f"Tool: {tool_name}")

    # Check if a tool is available
    if check_tool_available("cdxgen"):
        result = generate_sbom(
            tool_name="cdxgen",
            project_dir=Path("/path/to/project"),
            output_path=Path("/path/to/output.json"),
            ecosystem="python"
        )
"""

from pathlib import Path
from typing import Dict, List, Optional

import pluggy

from bom_bench.logging_config import get_logger
from bom_bench.plugins.hookspecs import SCAToolSpec
from bom_bench.models.sca import SCAToolInfo, SBOMResult

logger = get_logger(__name__)

# Create plugin manager with bom_bench namespace
pm = pluggy.PluginManager("bom_bench")
pm.add_hookspecs(SCAToolSpec)

# Track registered tools
_registered_tools: Dict[str, SCAToolInfo] = {}
_initialized: bool = False


def _load_bundled_plugins() -> None:
    """Load plugins bundled with bom-bench."""
    try:
        from bom_bench.plugins.bundled import cdxgen
        pm.register(cdxgen, name="bom_bench.plugins.bundled.cdxgen")
        logger.debug("Loaded bundled cdxgen plugin")
    except ImportError as e:
        logger.debug(f"Could not load bundled cdxgen plugin: {e}")

    try:
        from bom_bench.plugins.bundled import syft
        pm.register(syft, name="bom_bench.plugins.bundled.syft")
        logger.debug("Loaded bundled syft plugin")
    except ImportError as e:
        logger.debug(f"Could not load bundled syft plugin: {e}")


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
    global _registered_tools, _initialized

    if _initialized:
        return

    _registered_tools = {}

    # Load bundled plugins
    _load_bundled_plugins()

    # Load external plugins via entry points
    _load_external_plugins()

    # Collect tool registrations from all plugins
    results = pm.hook.bom_bench_register_sca_tools()
    for tool_list in results:
        if tool_list:
            for tool_info in tool_list:
                _registered_tools[tool_info.name] = tool_info
                logger.debug(f"Registered SCA tool: {tool_info.name}")

    _initialized = True
    logger.debug(f"Plugin system initialized with {len(_registered_tools)} tool(s)")


def reset_plugins() -> None:
    """Reset the plugin system (mainly for testing).

    Clears all registered tools, unregisters all plugins, and marks
    the system as uninitialized. The next call to get_registered_tools()
    or initialize_plugins() will re-initialize the system.
    """
    global _registered_tools, _initialized

    # Unregister all plugins from the plugin manager
    for plugin in list(pm.get_plugins()):
        try:
            pm.unregister(plugin)
        except Exception:
            pass

    _registered_tools = {}
    _initialized = False


def get_registered_tools() -> Dict[str, SCAToolInfo]:
    """Get all registered SCA tools.

    Returns:
        Dictionary mapping tool name to SCAToolInfo.
    """
    if not _initialized:
        initialize_plugins()
    return _registered_tools.copy()


def list_available_tools() -> List[str]:
    """Get list of available tool names.

    Returns:
        List of registered tool names.
    """
    return list(get_registered_tools().keys())


def get_tool_info(tool_name: str) -> Optional[SCAToolInfo]:
    """Get info for a specific tool.

    Args:
        tool_name: Name of the tool.

    Returns:
        SCAToolInfo or None if tool not registered.
    """
    return get_registered_tools().get(tool_name)


def check_tool_available(tool_name: str) -> bool:
    """Check if a specific tool is installed and available.

    Args:
        tool_name: Name of the tool to check.

    Returns:
        True if tool is available, False otherwise.
    """
    if tool_name not in get_registered_tools():
        return False

    results = pm.hook.bom_bench_check_tool_available(tool_name=tool_name)
    for result in results:
        if result is not None:
            return result
    return False


def generate_sbom(
    tool_name: str,
    project_dir: Path,
    output_path: Path,
    ecosystem: str,
    timeout: int = 120
) -> Optional[SBOMResult]:
    """Generate SBOM using a registered tool.

    Args:
        tool_name: Name of the SCA tool to use.
        project_dir: Directory containing project files.
        output_path: Where to write the SBOM.
        ecosystem: Package ecosystem (python, javascript, etc.)
        timeout: Execution timeout in seconds.

    Returns:
        SBOMResult with execution details, or None if tool not found.
    """
    if tool_name not in get_registered_tools():
        logger.warning(f"Tool '{tool_name}' not registered")
        return None

    results = pm.hook.bom_bench_generate_sbom(
        tool_name=tool_name,
        project_dir=project_dir,
        output_path=output_path,
        ecosystem=ecosystem,
        timeout=timeout
    )

    for result in results:
        if result is not None:
            return result

    logger.warning(f"No plugin handled SBOM generation for tool '{tool_name}'")
    return None


def get_plugins() -> List[Dict]:
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
    "initialize_plugins",
    "reset_plugins",
    "get_registered_tools",
    "list_available_tools",
    "get_tool_info",
    "check_tool_available",
    "generate_sbom",
    "get_plugins",
]
