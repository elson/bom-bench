"""Package manager plugin management.

Provides functions for working with package managers:
    from bom_bench.package_managers import (
        list_available_package_managers,
        check_pm_available,
        pm_generate_manifest,
        pm_run_lock,
        pm_get_output_dir,
        pm_validate_scenario,
        pm_generate_sbom_for_lock,
    )

Available plugins:
- uv: UV Python package manager
"""

from pathlib import Path
from typing import Dict, List, Optional

from bom_bench.logging_config import get_logger
from bom_bench.models.package_manager import PMInfo

logger = get_logger(__name__)

# Track registered package managers
_registered_pms: Dict[str, PMInfo] = {}


def _register_package_managers(pm) -> None:
    """Register package managers from plugins.

    Called by initialize_plugins() in bom_bench.plugins.

    Args:
        pm: The pluggy PluginManager instance
    """
    global _registered_pms
    _registered_pms = {}

    pm_results = pm.hook.register_package_managers()
    for pm_list in pm_results:
        if pm_list:
            for pm_info in pm_list:
                _registered_pms[pm_info.name] = pm_info
                logger.debug(f"Registered package manager: {pm_info.name}")


def _reset_pms() -> None:
    """Reset package manager registry.

    Called by reset_plugins() in bom_bench.plugins.
    """
    global _registered_pms
    _registered_pms = {}


def get_registered_package_managers() -> Dict[str, PMInfo]:
    """Get all registered package managers.

    Returns:
        Dictionary mapping PM name to PMInfo.
    """
    from bom_bench.plugins import initialize_plugins
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
    from bom_bench.plugins import pm, initialize_plugins

    initialize_plugins()

    if pm_name not in _registered_pms:
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
    from bom_bench.plugins import pm, initialize_plugins

    initialize_plugins()

    if pm_name not in _registered_pms:
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
    from bom_bench.plugins import pm, initialize_plugins

    initialize_plugins()

    if pm_name not in _registered_pms:
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
    from bom_bench.plugins import pm, initialize_plugins

    initialize_plugins()

    if pm_name not in _registered_pms:
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
    from bom_bench.plugins import pm, initialize_plugins

    initialize_plugins()

    if pm_name not in _registered_pms:
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
    from bom_bench.plugins import pm, initialize_plugins

    initialize_plugins()

    if pm_name not in _registered_pms:
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
    from bom_bench.plugins import pm, initialize_plugins

    initialize_plugins()

    if pm_name not in _registered_pms:
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


__all__ = [
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
