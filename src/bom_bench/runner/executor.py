"""Single fixture execution against an SCA tool."""

from bom_bench.benchmarking.comparison import (
    extract_purls_from_cyclonedx,
    load_actual_sbom,
    load_expected_sbom,
)
from bom_bench.logging import get_logger
from bom_bench.models.fixture import Fixture, FixtureSetEnvironment
from bom_bench.models.sandbox import SandboxConfig
from bom_bench.models.sca_tool import (
    BenchmarkResult,
    BenchmarkStatus,
    PurlMetrics,
    SCAToolConfig,
)
from bom_bench.sandbox.sandbox import Sandbox

logger = get_logger(__name__)


class FixtureExecutor:
    """Executes a single fixture against an SCA tool using a sandbox."""

    def __init__(self, config: SandboxConfig | None = None):
        """Initialize executor.

        Args:
            config: Sandbox configuration. Uses defaults if not provided.
        """
        self.config = config or SandboxConfig()

    def execute(
        self,
        fixture: Fixture,
        fixture_set_env: FixtureSetEnvironment,
        tool_config: SCAToolConfig,
    ) -> BenchmarkResult:
        """Execute a fixture against an SCA tool.

        Creates a sandbox, runs the tool, and compares results.

        Args:
            fixture: The fixture to execute
            fixture_set_env: Environment from the fixture set
            tool_config: SCA tool configuration

        Returns:
            BenchmarkResult with comparison metrics
        """
        # Check if fixture is satisfiable
        if not fixture.satisfiable:
            return BenchmarkResult(
                scenario_name=fixture.name,
                package_manager="fixture",
                tool_name=tool_config.name,
                status=BenchmarkStatus.UNSATISFIABLE,
                expected_satisfiable=False,
            )

        # Check if expected SBOM exists
        if fixture.files.expected_sbom is None:
            return BenchmarkResult(
                scenario_name=fixture.name,
                package_manager="fixture",
                tool_name=tool_config.name,
                status=BenchmarkStatus.MISSING_EXPECTED,
                error_message="No expected SBOM path",
            )

        # Run in sandbox
        with Sandbox(fixture, fixture_set_env, tool_config, self.config) as sandbox:
            sandbox_result = sandbox.run()

        if not sandbox_result.success:
            return BenchmarkResult(
                scenario_name=fixture.name,
                package_manager="fixture",
                tool_name=tool_config.name,
                status=BenchmarkStatus.SBOM_GENERATION_FAILED,
                error_message=sandbox_result.error_message,
            )

        # Load actual SBOM
        if sandbox_result.actual_sbom_path is None:
            return BenchmarkResult(
                scenario_name=fixture.name,
                package_manager="fixture",
                tool_name=tool_config.name,
                status=BenchmarkStatus.SBOM_GENERATION_FAILED,
                error_message="No SBOM path in result",
            )

        actual_sbom = load_actual_sbom(sandbox_result.actual_sbom_path)
        if actual_sbom is None:
            return BenchmarkResult(
                scenario_name=fixture.name,
                package_manager="fixture",
                tool_name=tool_config.name,
                status=BenchmarkStatus.PARSE_ERROR,
                error_message="Failed to parse actual SBOM",
                actual_sbom_path=sandbox_result.actual_sbom_path,
            )

        # Load expected SBOM
        expected_sbom, satisfiable = load_expected_sbom(
            fixture.files.expected_sbom,
            meta_path=fixture.files.meta,
        )

        if not satisfiable:
            return BenchmarkResult(
                scenario_name=fixture.name,
                package_manager="fixture",
                tool_name=tool_config.name,
                status=BenchmarkStatus.UNSATISFIABLE,
                expected_satisfiable=False,
            )

        if expected_sbom is None:
            return BenchmarkResult(
                scenario_name=fixture.name,
                package_manager="fixture",
                tool_name=tool_config.name,
                status=BenchmarkStatus.MISSING_EXPECTED,
                error_message="Failed to load expected SBOM",
            )

        # Compare PURLs
        expected_purls = extract_purls_from_cyclonedx(expected_sbom)
        actual_purls = extract_purls_from_cyclonedx(actual_sbom)
        metrics = PurlMetrics.calculate(expected_purls, actual_purls)

        return BenchmarkResult(
            scenario_name=fixture.name,
            package_manager="fixture",
            tool_name=tool_config.name,
            status=BenchmarkStatus.SUCCESS,
            metrics=metrics,
            expected_sbom_path=fixture.files.expected_sbom,
            actual_sbom_path=sandbox_result.actual_sbom_path,
        )
