"""Command-line interface for bom-bench."""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from bom_bench.config import (
    DEFAULT_PACKAGE_MANAGER,
    OUTPUT_DIR,
    UNIVERSAL_SCENARIOS_ONLY,
    EXCLUDE_NAME_PATTERNS,
)
from bom_bench.data.loader import ScenarioLoader
from bom_bench.models.scenario import ScenarioFilter, Scenario
from bom_bench.models.result import ProcessingResult, ProcessingStatus, Summary
from bom_bench.package_managers import get_package_manager, list_available_package_managers


class BomBenchCLI:
    """Command-line interface orchestrator for bom-bench."""

    def __init__(self):
        """Initialize CLI orchestrator."""
        self.scenario_loader = ScenarioLoader(auto_fetch=True)

    def parse_args(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """Parse command-line arguments.

        Args:
            args: Optional argument list (defaults to sys.argv)

        Returns:
            Parsed arguments namespace
        """
        parser = argparse.ArgumentParser(
            description="Generate package manager manifests and lock files from test scenarios",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Generate for default package manager (uv)
  bom-bench

  # Generate with lock files
  bom-bench --lock

  # Generate for multiple package managers
  bom-bench --package-managers uv,pip

  # Generate for all available package managers
  bom-bench --package-managers all

  # Filter specific scenarios
  bom-bench --scenarios fork-basic,local-simple
            """,
        )

        parser.add_argument(
            "--package-managers",
            "-pm",
            type=str,
            default=DEFAULT_PACKAGE_MANAGER,
            help=f"Comma-separated list of package managers to use, or 'all' (default: {DEFAULT_PACKAGE_MANAGER})",
        )

        parser.add_argument(
            "--lock",
            action="store_true",
            help="Generate lock files for each scenario",
        )

        parser.add_argument(
            "--scenarios",
            "-s",
            type=str,
            help="Comma-separated list of specific scenario names to process (optional)",
        )

        parser.add_argument(
            "--output-dir",
            "-o",
            type=Path,
            default=OUTPUT_DIR,
            help=f"Base output directory (default: {OUTPUT_DIR})",
        )

        parser.add_argument(
            "--no-universal-filter",
            action="store_true",
            help="Include scenarios without universal=true",
        )

        return parser.parse_args(args)

    def parse_package_managers(self, pm_arg: str) -> List[str]:
        """Parse package manager argument.

        Args:
            pm_arg: Package manager argument string (e.g., 'uv,pip' or 'all')

        Returns:
            List of package manager names

        Raises:
            ValueError: If package manager is not available
        """
        if pm_arg.lower() == "all":
            return list_available_package_managers()

        pms = [pm.strip() for pm in pm_arg.split(",")]
        available = list_available_package_managers()

        for pm in pms:
            if pm not in available:
                raise ValueError(
                    f"Unknown package manager: {pm}. "
                    f"Available: {', '.join(available)}"
                )

        return pms

    def create_filter(
        self,
        universal_only: bool = UNIVERSAL_SCENARIOS_ONLY,
        scenario_names: Optional[List[str]] = None
    ) -> ScenarioFilter:
        """Create scenario filter configuration.

        Args:
            universal_only: Only include scenarios with universal=true
            scenario_names: Optional specific scenario names to include

        Returns:
            ScenarioFilter instance
        """
        return ScenarioFilter(
            universal_only=universal_only,
            exclude_patterns=EXCLUDE_NAME_PATTERNS,
        )

    def filter_by_names(
        self,
        scenarios: List[Scenario],
        names: List[str]
    ) -> List[Scenario]:
        """Filter scenarios by specific names.

        Args:
            scenarios: List of scenarios to filter
            names: List of scenario names to include

        Returns:
            Filtered list of scenarios
        """
        name_set = set(names)
        return [s for s in scenarios if s.name in name_set]

    def process_scenario(
        self,
        scenario: Scenario,
        package_manager_name: str,
        output_base: Path
    ) -> ProcessingResult:
        """Process a single scenario for a package manager.

        Args:
            scenario: Scenario to process
            package_manager_name: Package manager name
            output_base: Base output directory

        Returns:
            ProcessingResult with status and details
        """
        pm = get_package_manager(package_manager_name)

        if pm is None:
            return ProcessingResult(
                scenario_name=scenario.name,
                status=ProcessingStatus.FAILED,
                package_manager=package_manager_name,
                error_message=f"Package manager '{package_manager_name}' not found"
            )

        # Validate scenario compatibility
        if not pm.validate_scenario(scenario):
            return ProcessingResult(
                scenario_name=scenario.name,
                status=ProcessingStatus.SKIPPED,
                package_manager=package_manager_name,
                error_message=f"Scenario not compatible with {package_manager_name}"
            )

        try:
            # Get output directory (hierarchical: output/{pm}/{scenario}/)
            output_dir = pm.get_output_dir(output_base, scenario.name)

            # Generate manifest
            manifest_path = pm.generate_manifest(scenario, output_dir)

            print(f"Generated: {manifest_path}")

            # Log SBOM generation if it exists
            sbom_path = output_dir / "expected.cdx.json"
            if sbom_path.exists():
                print(f"Generated expected SBOM: {sbom_path}")

            return ProcessingResult(
                scenario_name=scenario.name,
                status=ProcessingStatus.SUCCESS,
                package_manager=package_manager_name,
                output_dir=output_dir
            )

        except Exception as e:
            return ProcessingResult(
                scenario_name=scenario.name,
                status=ProcessingStatus.FAILED,
                package_manager=package_manager_name,
                error_message=str(e)
            )

    def run(self, args: Optional[List[str]] = None) -> int:
        """Run the CLI application.

        Args:
            args: Optional argument list (defaults to sys.argv)

        Returns:
            Exit code (0 for success, 1 for error)
        """
        try:
            # Parse arguments
            parsed_args = self.parse_args(args)

            # Parse package managers
            try:
                package_managers = self.parse_package_managers(parsed_args.package_managers)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1

            # Parse specific scenario names if provided
            scenario_names = None
            if parsed_args.scenarios:
                scenario_names = [s.strip() for s in parsed_args.scenarios.split(",")]

            print(f"Package managers: {', '.join(package_managers)}")
            print()

            # Process each package manager
            for pm_name in package_managers:
                print(f"=== {pm_name.upper()} ===")

                # Create filter
                filter_config = self.create_filter(
                    universal_only=not parsed_args.no_universal_filter
                )

                # Load scenarios for this package manager
                scenarios = self.scenario_loader.load_for_package_manager(
                    pm_name,
                    filter_config=filter_config
                )

                if not scenarios:
                    print(f"Warning: No scenarios found for {pm_name}")
                    print()
                    continue

                # Filter by specific names if requested
                if scenario_names:
                    scenarios = self.filter_by_names(scenarios, scenario_names)

                    if not scenarios:
                        print(f"Warning: None of the specified scenarios found for {pm_name}")
                        print()
                        continue

                print(f"Found {len(scenarios)} scenarios")

                # Create summary
                summary = Summary(
                    total_scenarios=len(scenarios),
                    package_manager=pm_name,
                    data_source=scenarios[0].source if scenarios else None
                )

                # Get package manager instance
                pm = get_package_manager(pm_name)
                if pm is None:
                    print(f"Error: Package manager '{pm_name}' not available", file=sys.stderr)
                    continue

                # Process each scenario
                for scenario in scenarios:
                    result = self.process_scenario(
                        scenario,
                        pm_name,
                        parsed_args.output_dir
                    )
                    summary.add_processing_result(result)

                    # Print errors
                    if result.status == ProcessingStatus.FAILED:
                        print(f"  Error: {scenario.name}: {result.error_message}", file=sys.stderr)

                # Generate lock files if requested
                if parsed_args.lock and summary.processed > 0:
                    print(f"\nGenerating lock files for {summary.processed} scenarios...")

                    for scenario in scenarios:
                        # Skip if scenario wasn't processed successfully
                        output_dir = pm.get_output_dir(parsed_args.output_dir, scenario.name)
                        if not output_dir.exists():
                            continue

                        print(f"  Locking: {scenario.name}...", end=" ", flush=True)

                        lock_result = pm.run_lock(
                            output_dir,
                            scenario.name
                        )
                        summary.add_lock_result(lock_result)

                        # Print result
                        if lock_result.status.value == "success":
                            print("✓")
                        else:
                            print(f"✗ ({lock_result.status.value})")

                # Print summary
                summary.print_summary(include_lock=parsed_args.lock)
                print()

            return 0

        except KeyboardInterrupt:
            print("\nInterrupted by user", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1


def main(args: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI.

    Args:
        args: Optional argument list (defaults to sys.argv)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    cli = BomBenchCLI()
    return cli.run(args)


if __name__ == "__main__":
    sys.exit(main())
