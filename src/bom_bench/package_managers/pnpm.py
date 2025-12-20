"""pnpm package manager implementation (STUB - Not yet implemented).

This is a stub implementation showing how to add pnpm as a package manager.
pnpm is a fast, disk space-efficient package manager for Node.js/JavaScript.

Implementation TODO:
- Generate package.json files from scenarios
- Translate Python package concepts to npm packages (if needed)
- Run pnpm install --lockfile-only
- Handle workspace and monorepo scenarios
"""

from pathlib import Path
from bom_bench.models.scenario import Scenario
from bom_bench.models.result import LockResult, LockStatus
from bom_bench.package_managers.base import PackageManager


class PnpmPackageManager(PackageManager):
    """pnpm package manager implementation (STUB).

    pnpm is a JavaScript/Node.js package manager that:
    - Uses a content-addressable store for disk efficiency
    - Supports monorepos and workspaces
    - Generates pnpm-lock.yaml for reproducible builds

    Output structure:
    - output/pnpm/{scenario}/
        - package.json (project manifest)
        - pnpm-lock.yaml (lock file)
        - pnpm-install-output.txt (command output log)

    Data source compatibility:
    - Supports: pnpm-tests (pnpm test cases from git repo)
    - Future: npm registry fixtures, custom JavaScript scenarios

    Translation notes:
    - Python packages → npm packages (may need mapping)
    - Version constraints: Similar but different syntax
    - Platform markers → OS-specific package.json conditions
    """

    name = "pnpm"
    ecosystem = "javascript"

    def generate_manifest(
        self,
        scenario: Scenario,
        output_dir: Path
    ) -> Path:
        """Generate package.json for pnpm.

        Args:
            scenario: Scenario to generate manifest for
            output_dir: Directory where manifest file should be written

        Returns:
            Path to the generated package.json file

        Raises:
            NotImplementedError: This is a stub implementation
        """
        raise NotImplementedError(
            "pnpm package manager is not yet implemented. "
            "See src/bom_bench/package_managers/pnpm.py for implementation guide."
        )

        # TODO: Implementation outline:
        # 1. Use src/bom_bench/generators/json.py for package.json generation
        # 2. Translate scenario.root.requires to package.json dependencies
        # 3. Handle version constraints and platform-specific deps
        # 4. Return path to package.json

    def run_lock(
        self,
        project_dir: Path,
        scenario_name: str,
        timeout: int = 120
    ) -> LockResult:
        """Execute pnpm install --lockfile-only and capture output.

        Args:
            project_dir: Directory containing package.json
            scenario_name: Name of the scenario (for logging)
            timeout: Command timeout in seconds

        Returns:
            LockResult with execution details

        Raises:
            NotImplementedError: This is a stub implementation
        """
        raise NotImplementedError(
            "pnpm package manager is not yet implemented. "
            "See src/bom_bench/package_managers/pnpm.py for implementation guide."
        )

        # TODO: Implementation outline:
        # 1. Run: pnpm install --lockfile-only
        # 2. Capture stdout/stderr to pnpm-install-output.txt
        # 3. Check if pnpm-lock.yaml was generated
        # 4. Return LockResult with status and file paths

    def validate_scenario(self, scenario: Scenario) -> bool:
        """Check if scenario is compatible with pnpm.

        Args:
            scenario: Scenario to validate

        Returns:
            True if scenario is compatible
        """
        # pnpm requires scenarios from pnpm-tests data source
        return scenario.source in ["pnpm-tests"]
