"""Package manager implementations and registry."""

from typing import Dict, Type, Optional

from bom_bench.package_managers.base import PackageManager
from bom_bench.package_managers.uv import UVPackageManager


# Package manager registry
PACKAGE_MANAGERS: Dict[str, Type[PackageManager]] = {
    "uv": UVPackageManager,
}


def get_package_manager(name: str) -> Optional[PackageManager]:
    """Get a package manager instance by name.

    Args:
        name: Package manager name (e.g., 'uv', 'pip')

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
    "PackageManager",
    "UVPackageManager",
    "PACKAGE_MANAGERS",
    "get_package_manager",
    "list_available_package_managers",
]
