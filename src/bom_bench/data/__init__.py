"""Data source registry and utilities."""

from pathlib import Path

from bom_bench.config import DATA_DIR
from bom_bench.data.sources.packse import PackseDataSource

# Data source registry
DATA_SOURCES: dict[str, type[PackseDataSource]] = {
    "packse": PackseDataSource,
}


def get_data_source(name: str, data_dir: Path | None = None) -> PackseDataSource:
    """Get a data source instance by name.

    Args:
        name: Data source name (e.g., 'packse')
        data_dir: Optional custom data directory (defaults to DATA_DIR/{name})

    Returns:
        DataSource instance

    Raises:
        ValueError: If data source name is not registered
    """
    if name not in DATA_SOURCES:
        available = ", ".join(DATA_SOURCES.keys())
        raise ValueError(f"Unknown data source: {name}. Available: {available}")

    source_class = DATA_SOURCES[name]

    if data_dir is None:
        data_dir = DATA_DIR / name

    return source_class(data_dir)


def get_available_sources() -> list[str]:
    """Get list of available data source names.

    Returns:
        List of registered data source names
    """
    return list(DATA_SOURCES.keys())


def get_sources_for_pm(package_manager: str) -> list[str]:
    """Get data sources that support a specific package manager.

    Args:
        package_manager: Package manager name (e.g., 'uv', 'pip')

    Returns:
        List of data source names that support the package manager
    """
    compatible_sources = []

    for name in DATA_SOURCES:
        source = get_data_source(name)
        if package_manager in source.supported_pms:
            compatible_sources.append(name)

    return compatible_sources


__all__ = [
    "PackseDataSource",
    "DATA_SOURCES",
    "get_data_source",
    "get_available_sources",
    "get_sources_for_pm",
]
