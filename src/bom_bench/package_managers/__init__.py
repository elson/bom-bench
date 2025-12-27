"""Package manager implementations and registry.

This module provides backward compatibility during the migration
to the plugin-based architecture. New code should use the plugin
functions from bom_bench.plugins instead.
"""

from typing import Optional

from bom_bench.package_managers.uv import UVPackageManager


# Package manager registry (for backward compatibility)
PACKAGE_MANAGERS = {
    "uv": UVPackageManager,
}


def get_package_manager(name: str) -> Optional[UVPackageManager]:
    """Get a package manager instance by name.

    Args:
        name: Package manager name (e.g., 'uv')

    Returns:
        Package manager instance, or None if not found
    """
    pm_class = PACKAGE_MANAGERS.get(name)
    if pm_class:
        return pm_class()
    return None


def list_available_package_managers() -> list[str]:
    """Get list of available package manager names.

    Returns:
        List of package manager names
    """
    return list(PACKAGE_MANAGERS.keys())


__all__ = [
    "UVPackageManager",
    "PACKAGE_MANAGERS",
    "get_package_manager",
    "list_available_package_managers",
]
