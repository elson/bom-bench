"""Package manager plugin management.

Provides functions for working with package managers:
    from bom_bench.package_managers import (
        list_available_package_managers,
        check_package_manager_available,
        get_package_manager_info,
        package_manager_process_scenario,
    )

Available plugins:
- uv: UV Python package manager
"""

from pathlib import Path

from bom_bench.logging_config import get_logger
from bom_bench.models.package_manager import PMInfo, ProcessScenarioResult

logger = get_logger(__name__)

# Track registered package managers
_registered_pms: dict[str, PMInfo] = {}


def _register_package_managers(pm) -> None:
    """Register package managers from plugins.

    Called by initialize_plugins() in bom_bench.plugins.

    Args:
        pm: The pluggy PluginManager instance
    """
    global _registered_pms
    _registered_pms = {}

    for pm_data in pm.hook.register_package_managers():
        if pm_data:
            pm_info = PMInfo.from_dict(pm_data)
            _registered_pms[pm_info.name] = pm_info
            logger.debug(f"Registered package manager: {pm_info.name}")


def _reset_package_managers() -> None:
    """Reset package manager registry.

    Called by reset_plugins() in bom_bench.plugins.
    """
    global _registered_pms
    _registered_pms = {}


def get_registered_package_managers() -> dict[str, PMInfo]:
    """Get all registered package managers.

    Returns:
        Dictionary mapping PM name to PMInfo.
    """
    from bom_bench.plugins import initialize_plugins

    initialize_plugins()
    return _registered_pms.copy()


def list_available_package_managers() -> list[str]:
    """Get list of available package manager names.

    Returns:
        List of registered PM names.
    """
    return list(get_registered_package_managers().keys())


def get_package_manager_info(pm_name: str) -> PMInfo | None:
    """Get info for a specific package manager.

    Args:
        pm_name: Name of the package manager.

    Returns:
        PMInfo or None if PM not registered.
    """
    return get_registered_package_managers().get(pm_name)


def check_package_manager_available(pm_name: str) -> bool:
    """Check if a specific package manager is installed and available.

    Args:
        pm_name: Name of the PM to check.

    Returns:
        True if PM is available, False otherwise.
    """
    pms = get_registered_package_managers()
    if pm_name not in pms:
        return False
    return pms[pm_name].installed


def package_manager_process_scenario(
    pm_name: str, scenario, output_dir: Path, timeout: int = 120
) -> ProcessScenarioResult | None:
    """Process a scenario: generate manifest, lock, and SBOM (new atomic operation).

    This is the new simplified interface that combines generate_manifest, run_lock,
    and generate_sbom_for_lock into a single atomic operation.

    Args:
        pm_name: Name of the package manager.
        scenario: Scenario to process.
        output_dir: Output directory for scenario files.
        timeout: Timeout in seconds.

    Returns:
        ProcessScenarioResult, or None if PM not found.
    """
    from bom_bench.plugins import initialize_plugins, pm

    initialize_plugins()

    if pm_name not in _registered_pms:
        logger.warning(f"Package manager '{pm_name}' not registered")
        return None

    results = pm.hook.process_scenario(
        pm_name=pm_name, scenario=scenario, output_dir=output_dir, timeout=timeout
    )

    for result in results:
        if result is not None:
            # Convert dict to ProcessScenarioResult
            return ProcessScenarioResult.from_dict(result)

    logger.warning(f"No plugin handled process_scenario for PM '{pm_name}'")
    return None


__all__ = [
    "get_registered_package_managers",
    "list_available_package_managers",
    "get_package_manager_info",
    "check_package_manager_available",
    "package_manager_process_scenario",
]
