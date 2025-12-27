"""Package manager plugins.

This package contains package manager plugin implementations.
Each plugin registers with the bom-bench plugin system.

For usage, import from bom_bench.plugins:
    from bom_bench.plugins import (
        list_available_package_managers,
        check_pm_available,
        pm_get_output_dir,
        pm_validate_scenario,
        pm_generate_manifest,
        pm_run_lock,
        pm_generate_sbom_for_lock,
    )
"""

# Note: Do not import from this module directly.
# Use bom_bench.plugins for all package manager functionality.
