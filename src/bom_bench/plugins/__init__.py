"""Plugin system for bom-bench.

Uses Pluggy for plugin discovery and hook management.
Follows the Datasette pattern for plugin architecture.

Usage:
    from bom_bench.plugins import (
        initialize_plugins,
        get_registered_tools,
        list_available_tools,
        check_tool_available,
        generate_sbom,
        get_registered_package_managers,
        pm_load_scenarios,
        pm_generate_manifest,
        pm_run_lock,
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

import importlib
from pathlib import Path
from typing import Dict, List, Optional

import pluggy

from bom_bench.logging_config import get_logger
from bom_bench.plugins.hookspecs import SCAToolSpec, PackageManagerSpec
from bom_bench.models.sca import SCAToolInfo, SBOMResult
from bom_bench.models.package_manager import PMInfo

logger = get_logger(__name__)


# Default plugins bundled with bom-bench
# These are loaded automatically on initialization
DEFAULT_PLUGINS = (
    "bom_bench.package_managers.uv",
    "bom_bench.sca_tools.cdxgen",
    "bom_bench.sca_tools.syft",
)


# Create plugin manager with bom_bench namespace
pm = pluggy.PluginManager("bom_bench")
pm.add_hookspecs(SCAToolSpec)
pm.add_hookspecs(PackageManagerSpec)

# Track registered tools and package managers
_registered_tools: Dict[str, SCAToolInfo] = {}
_registered_pms: Dict[str, PMInfo] = {}
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
    via entry points. Collects tool and PM registrations from all plugins.

    This function is idempotent - calling it multiple times has no effect
    after the first call.
    """
    global _registered_tools, _registered_pms, _initialized

    if _initialized:
        return

    _registered_tools = {}
    _registered_pms = {}

    # Load default plugins
    _load_default_plugins()

    # Load external plugins via entry points
    _load_external_plugins()

    # Collect SCA tool registrations
    # Each plugin returns a single dict, which we convert to SCAToolInfo
    tool_results = pm.hook.register_sca_tools()
    for tool_data in tool_results:
        if tool_data:
            tool_info = SCAToolInfo.from_dict(tool_data)
            _registered_tools[tool_info.name] = tool_info
            logger.debug(f"Registered SCA tool: {tool_info.name}")

    # Collect package manager registrations
    pm_results = pm.hook.register_package_managers()
    for pm_list in pm_results:
        if pm_list:
            for pm_info in pm_list:
                _registered_pms[pm_info.name] = pm_info
                logger.debug(f"Registered package manager: {pm_info.name}")

    _initialized = True
    logger.debug(
        f"Plugin system initialized with {len(_registered_tools)} tool(s) "
        f"and {len(_registered_pms)} package manager(s)"
    )


def reset_plugins() -> None:
    """Reset the plugin system (mainly for testing).

    Clears all registered tools and PMs, unregisters all plugins, and marks
    the system as uninitialized. The next call to get_registered_tools()
    or initialize_plugins() will re-initialize the system.
    """
    global _registered_tools, _registered_pms, _initialized

    # Unregister all plugins from the plugin manager
    for plugin in list(pm.get_plugins()):
        try:
            pm.unregister(plugin)
        except Exception:
            pass

    _registered_tools = {}
    _registered_pms = {}
    _initialized = False


# =============================================================================
# SCA Tool Functions
# =============================================================================


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

    Uses the 'installed' field from tool registration.

    Args:
        tool_name: Name of the tool to check.

    Returns:
        True if tool is available, False otherwise.
    """
    tools = get_registered_tools()
    if tool_name not in tools:
        return False
    return tools[tool_name].installed


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

    results = pm.hook.generate_sbom(
        tool_name=tool_name,
        project_dir=project_dir,
        output_path=output_path,
        ecosystem=ecosystem,
        timeout=timeout
    )

    # Plugins return dicts, convert to SBOMResult
    for result in results:
        if result is not None:
            return SBOMResult.from_dict(result)

    logger.warning(f"No plugin handled SBOM generation for tool '{tool_name}'")
    return None


# =============================================================================
# Package Manager Functions
# =============================================================================


def get_registered_package_managers() -> Dict[str, PMInfo]:
    """Get all registered package managers.

    Returns:
        Dictionary mapping PM name to PMInfo.
    """
    if not _initialized:
        initialize_plugins()
    return _registered_pms.copy()


def list_available_package_managers() -> List[str]:
    """Get list of available package manager names.

    Returns:
        List of registered PM names.
    """
    return list(get_registered_package_managers().keys())


def get_pm_info(pm_name: str) -> Optional[PMInfo]:
    """Get info for a specific package manager.

    Args:
        pm_name: Name of the package manager.

    Returns:
        PMInfo or None if PM not registered.
    """
    return get_registered_package_managers().get(pm_name)


def check_pm_available(pm_name: str) -> bool:
    """Check if a specific package manager is installed and available.

    Args:
        pm_name: Name of the PM to check.

    Returns:
        True if PM is available, False otherwise.
    """
    if pm_name not in get_registered_package_managers():
        return False

    results = pm.hook.check_pm_available(pm_name=pm_name)
    for result in results:
        if result is not None:
            return result
    return False


def pm_load_scenarios(pm_name: str, data_dir: Path) -> List:
    """Load scenarios for a package manager.

    Args:
        pm_name: Name of the package manager.
        data_dir: Base data directory.

    Returns:
        List of scenarios.
    """
    if pm_name not in get_registered_package_managers():
        logger.warning(f"Package manager '{pm_name}' not registered")
        return []

    results = pm.hook.load_scenarios(pm_name=pm_name, data_dir=data_dir)
    for result in results:
        if result is not None:
            return result

    logger.warning(f"No plugin handled scenario loading for PM '{pm_name}'")
    return []


def pm_generate_manifest(pm_name: str, scenario, output_dir: Path) -> Optional[Path]:
    """Generate manifest for a scenario.

    Args:
        pm_name: Name of the package manager.
        scenario: Scenario to generate manifest for.
        output_dir: Output directory.

    Returns:
        Path to manifest file, or None if failed.
    """
    if pm_name not in get_registered_package_managers():
        logger.warning(f"Package manager '{pm_name}' not registered")
        return None

    results = pm.hook.generate_manifest(
        pm_name=pm_name,
        scenario=scenario,
        output_dir=output_dir
    )

    for result in results:
        if result is not None:
            return result

    logger.warning(f"No plugin handled manifest generation for PM '{pm_name}'")
    return None


def pm_run_lock(
    pm_name: str,
    project_dir: Path,
    scenario_name: str,
    timeout: int = 120
):
    """Run lock command for a project.

    Args:
        pm_name: Name of the package manager.
        project_dir: Directory containing manifest.
        scenario_name: Name of scenario.
        timeout: Timeout in seconds.

    Returns:
        LockResult, or None if failed.
    """
    if pm_name not in get_registered_package_managers():
        logger.warning(f"Package manager '{pm_name}' not registered")
        return None

    results = pm.hook.run_lock(
        pm_name=pm_name,
        project_dir=project_dir,
        scenario_name=scenario_name,
        timeout=timeout
    )

    for result in results:
        if result is not None:
            return result

    logger.warning(f"No plugin handled lock for PM '{pm_name}'")
    return None


def pm_get_output_dir(pm_name: str, base_dir: Path, scenario_name: str) -> Optional[Path]:
    """Get output directory for a package manager scenario.

    Args:
        pm_name: Name of the package manager.
        base_dir: Base output directory.
        scenario_name: Name of the scenario.

    Returns:
        Path to scenario output directory, or None if PM not found.
    """
    if pm_name not in get_registered_package_managers():
        logger.warning(f"Package manager '{pm_name}' not registered")
        return None

    results = pm.hook.get_output_dir(
        pm_name=pm_name,
        base_dir=base_dir,
        scenario_name=scenario_name
    )

    for result in results:
        if result is not None:
            return result

    logger.warning(f"No plugin handled get_output_dir for PM '{pm_name}'")
    return None


def pm_validate_scenario(pm_name: str, scenario) -> bool:
    """Check if scenario is compatible with package manager.

    Args:
        pm_name: Name of the package manager.
        scenario: Scenario to validate.

    Returns:
        True if compatible, False otherwise.
    """
    if pm_name not in get_registered_package_managers():
        return False

    results = pm.hook.validate_scenario(
        pm_name=pm_name,
        scenario=scenario
    )

    for result in results:
        if result is not None:
            return result

    return False  # Default to not compatible


def pm_generate_sbom_for_lock(
    pm_name: str,
    scenario,
    output_dir: Path,
    lock_result
) -> Optional[Path]:
    """Generate SBOM and meta files from lock result.

    Args:
        pm_name: Name of the package manager.
        scenario: Scenario being processed.
        output_dir: Scenario output directory.
        lock_result: Result of lock operation.

    Returns:
        Path to generated file, or None if failed.
    """
    if pm_name not in get_registered_package_managers():
        logger.warning(f"Package manager '{pm_name}' not registered")
        return None

    results = pm.hook.generate_sbom_for_lock(
        pm_name=pm_name,
        scenario=scenario,
        output_dir=output_dir,
        lock_result=lock_result
    )

    for result in results:
        if result is not None:
            return result

    logger.warning(f"No plugin handled generate_sbom_for_lock for PM '{pm_name}'")
    return None


# =============================================================================
# Plugin Info Functions
# =============================================================================


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
    # Plugin management
    "pm",
    "DEFAULT_PLUGINS",
    "initialize_plugins",
    "reset_plugins",
    "get_plugins",
    # SCA tools
    "get_registered_tools",
    "list_available_tools",
    "get_tool_info",
    "check_tool_available",
    "generate_sbom",
    # Package managers
    "get_registered_package_managers",
    "list_available_package_managers",
    "get_pm_info",
    "check_pm_available",
    "pm_load_scenarios",
    "pm_generate_manifest",
    "pm_run_lock",
    "pm_get_output_dir",
    "pm_validate_scenario",
    "pm_generate_sbom_for_lock",
]
