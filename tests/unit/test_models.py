"""Tests for data models."""

from pathlib import Path

from bom_bench.models.data_source import PACKSE_INFO, DataSourceInfo
from bom_bench.models.package_manager import (
    UV_INFO,
    PackageManagerInfo,
    PMInfo,
    ProcessScenarioResult,
    ProcessStatus,
)
from bom_bench.models.result import (
    LockResult,
    LockStatus,
    ProcessingResult,
    ProcessingStatus,
    Summary,
)
from bom_bench.models.scenario import (
    Requirement,
    ResolverOptions,
    Root,
    Scenario,
    ScenarioFilter,
)


class TestRequirement:
    """Tests for Requirement model."""

    def test_create_requirement(self):
        """Test creating a Requirement."""
        req = Requirement(requirement="package-a>=1.0.0")
        assert req.requirement == "package-a>=1.0.0"
        assert req.extras == []

    def test_requirement_with_extras(self):
        """Test Requirement with extras."""
        req = Requirement(requirement="package-a[dev]>=1.0.0", extras=["dev"])
        assert req.requirement == "package-a[dev]>=1.0.0"
        assert req.extras == ["dev"]

    def test_requirement_from_dict(self):
        """Test creating Requirement from dictionary."""
        data = {"requirement": "package-b<2.0.0", "extras": ["test", "docs"]}
        req = Requirement.from_dict(data)
        assert req.requirement == "package-b<2.0.0"
        assert req.extras == ["test", "docs"]


class TestRoot:
    """Tests for Root model."""

    def test_create_root(self):
        """Test creating a Root."""
        req1 = Requirement(requirement="package-a>=1.0.0")
        req2 = Requirement(requirement="package-b<2.0.0")
        root = Root(requires=[req1, req2], requires_python=">=3.12")

        assert len(root.requires) == 2
        assert root.requires_python == ">=3.12"

    def test_root_from_dict(self):
        """Test creating Root from dictionary."""
        data = {
            "requires": [
                {"requirement": "package-a>=1.0.0"},
                {"requirement": "package-b<2.0.0"},
            ],
            "requires_python": ">=3.12",
        }
        root = Root.from_dict(data)

        assert len(root.requires) == 2
        assert root.requires[0].requirement == "package-a>=1.0.0"
        assert root.requires_python == ">=3.12"


class TestResolverOptions:
    """Tests for ResolverOptions model."""

    def test_create_resolver_options(self):
        """Test creating ResolverOptions."""
        opts = ResolverOptions(universal=True, required_environments=["sys_platform == 'linux'"])
        assert opts.universal is True
        assert len(opts.required_environments) == 1

    def test_resolver_options_defaults(self):
        """Test ResolverOptions defaults."""
        opts = ResolverOptions()
        assert opts.universal is False
        assert opts.required_environments == []

    def test_resolver_options_from_dict(self):
        """Test creating ResolverOptions from dictionary."""
        data = {"universal": True, "required_environments": ["python_version >= '3.8'"]}
        opts = ResolverOptions.from_dict(data)

        assert opts.universal is True
        assert opts.required_environments == ["python_version >= '3.8'"]


class TestScenario:
    """Tests for Scenario model."""

    def test_create_scenario(self):
        """Test creating a Scenario."""
        root = Root(requires=[Requirement(requirement="package-a>=1.0.0")])
        resolver = ResolverOptions(universal=True)
        scenario = Scenario(
            name="test-scenario",
            root=root,
            resolver_options=resolver,
            description="A test scenario",
        )

        assert scenario.name == "test-scenario"
        assert scenario.description == "A test scenario"
        assert scenario.source == "packse"
        assert scenario.resolver_options.universal is True

    def test_scenario_from_dict(self):
        """Test creating Scenario from dictionary."""
        data = {
            "name": "test-scenario",
            "root": {
                "requires": [{"requirement": "package-a>=1.0.0"}],
                "requires_python": ">=3.12",
            },
            "resolver_options": {"universal": True},
            "description": "Test description",
        }
        scenario = Scenario.from_dict(data, source="packse")

        assert scenario.name == "test-scenario"
        assert scenario.root.requires_python == ">=3.12"
        assert scenario.resolver_options.universal is True
        assert scenario.description == "Test description"
        assert scenario.source == "packse"

    def test_scenario_to_dict(self):
        """Test converting Scenario to dictionary for plugin injection."""
        from bom_bench.models.scenario import Expected, ExpectedPackage

        root = Root(
            requires=[Requirement(requirement="package-a>=1.0.0", extras=["dev"])],
            requires_python=">=3.12",
        )
        resolver = ResolverOptions(universal=True)
        expected = Expected(
            packages=[ExpectedPackage(name="package-a", version="1.0.0")],
            satisfiable=True,
        )
        scenario = Scenario(
            name="test-scenario",
            root=root,
            resolver_options=resolver,
            description="A test scenario",
            expected=expected,
            source="packse",
        )

        result = scenario.to_dict()

        assert result["name"] == "test-scenario"
        assert result["description"] == "A test scenario"
        assert result["source"] == "packse"
        assert result["root"]["requires_python"] == ">=3.12"
        assert result["root"]["requires"][0]["requirement"] == "package-a>=1.0.0"
        assert result["root"]["requires"][0]["extras"] == ["dev"]
        assert result["resolver_options"]["universal"] is True
        assert result["expected"]["satisfiable"] is True
        assert result["expected"]["packages"][0]["name"] == "package-a"
        assert result["expected"]["packages"][0]["version"] == "1.0.0"

    def test_scenario_to_dict_roundtrip(self):
        """Test that from_dict(to_dict(scenario)) preserves data."""
        from bom_bench.models.scenario import Expected, ExpectedPackage

        original = Scenario(
            name="roundtrip-test",
            root=Root(
                requires=[Requirement(requirement="pkg>=1.0")],
                requires_python=">=3.10",
            ),
            resolver_options=ResolverOptions(universal=True),
            expected=Expected(
                packages=[ExpectedPackage(name="pkg", version="1.0.0")],
                satisfiable=True,
            ),
        )

        reconstructed = Scenario.from_dict(original.to_dict(), source=original.source)

        assert reconstructed.name == original.name
        assert reconstructed.root.requires_python == original.root.requires_python
        assert len(reconstructed.root.requires) == len(original.root.requires)
        assert reconstructed.resolver_options.universal == original.resolver_options.universal


class TestScenarioFilter:
    """Tests for ScenarioFilter."""

    def test_filter_universal(self):
        """Test filtering by universal flag."""
        filter_config = ScenarioFilter(universal_only=True)

        scenario_universal = Scenario(
            name="test",
            root=Root(),
            resolver_options=ResolverOptions(universal=True),
        )
        scenario_not_universal = Scenario(
            name="test",
            root=Root(),
            resolver_options=ResolverOptions(universal=False),
        )

        assert filter_config.matches(scenario_universal) is True
        assert filter_config.matches(scenario_not_universal) is False

    def test_filter_exclude_patterns(self):
        """Test filtering by exclude patterns."""
        filter_config = ScenarioFilter(
            universal_only=False,
            exclude_patterns=["example", "test"],
        )

        scenario_normal = Scenario(
            name="normal-scenario",
            root=Root(),
            resolver_options=ResolverOptions(),
        )
        scenario_example = Scenario(
            name="example-scenario",
            root=Root(),
            resolver_options=ResolverOptions(),
        )

        assert filter_config.matches(scenario_normal) is True
        assert filter_config.matches(scenario_example) is False

    def test_filter_by_source(self):
        """Test filtering by data source."""
        filter_config = ScenarioFilter(
            universal_only=False,
            include_sources=["packse"],
        )

        scenario_packse = Scenario(
            name="test",
            root=Root(),
            resolver_options=ResolverOptions(),
            source="packse",
        )
        scenario_pnpm = Scenario(
            name="test",
            root=Root(),
            resolver_options=ResolverOptions(),
            source="pnpm-tests",
        )

        assert filter_config.matches(scenario_packse) is True
        assert filter_config.matches(scenario_pnpm) is False


class TestProcessingResult:
    """Tests for ProcessingResult model."""

    def test_create_processing_result(self):
        """Test creating a ProcessingResult."""
        result = ProcessingResult(
            scenario_name="test-scenario",
            status=ProcessingStatus.SUCCESS,
            package_manager="uv",
            output_dir=Path("/output/uv/test-scenario"),
        )

        assert result.scenario_name == "test-scenario"
        assert result.status == ProcessingStatus.SUCCESS
        assert result.package_manager == "uv"
        assert result.output_dir == Path("/output/uv/test-scenario")
        assert result.error_message is None


class TestLockResult:
    """Tests for LockResult model."""

    def test_create_lock_result(self):
        """Test creating a LockResult."""
        result = LockResult(
            scenario_name="test-scenario",
            package_manager="uv",
            status=LockStatus.SUCCESS,
            exit_code=0,
            lock_file=Path("/output/uv/test-scenario/uv.lock"),
        )

        assert result.scenario_name == "test-scenario"
        assert result.status == LockStatus.SUCCESS
        assert result.exit_code == 0
        assert result.package_manager == "uv"


class TestSummary:
    """Tests for Summary model."""

    def test_create_summary(self):
        """Test creating a Summary."""
        summary = Summary(total_scenarios=100)
        assert summary.total_scenarios == 100
        assert summary.processed == 0
        assert summary.skipped == 0
        assert summary.failed == 0

    def test_add_processing_results(self):
        """Test adding processing results to summary."""
        summary = Summary(total_scenarios=3)

        result1 = ProcessingResult(
            scenario_name="s1",
            status=ProcessingStatus.SUCCESS,
            package_manager="uv",
        )
        result2 = ProcessingResult(
            scenario_name="s2",
            status=ProcessingStatus.SKIPPED,
            package_manager="uv",
        )
        result3 = ProcessingResult(
            scenario_name="s3",
            status=ProcessingStatus.FAILED,
            package_manager="uv",
            error_message="Error",
        )

        summary.add_processing_result(result1)
        summary.add_processing_result(result2)
        summary.add_processing_result(result3)

        assert summary.processed == 1
        assert summary.skipped == 1
        assert summary.failed == 1


class TestPackageManagerInfo:
    """Tests for PackageManagerInfo model."""

    def test_create_package_manager_info(self):
        """Test creating PackageManagerInfo."""
        info = PackageManagerInfo(
            name="uv",
            display_name="UV",
            manifest_files=["pyproject.toml"],
            lock_files=["uv.lock"],
            ecosystem="python",
        )

        assert info.name == "uv"
        assert info.display_name == "UV"
        assert info.ecosystem == "python"
        assert "pyproject.toml" in info.manifest_files

    def test_uv_info_constant(self):
        """Test predefined UV_INFO constant."""
        assert UV_INFO.name == "uv"
        assert UV_INFO.ecosystem == "python"
        assert "uv.lock" in UV_INFO.lock_files


class TestDataSourceInfo:
    """Tests for DataSourceInfo model."""

    def test_create_data_source_info(self):
        """Test creating DataSourceInfo."""
        info = DataSourceInfo(
            name="packse",
            display_name="Packse",
            supported_pms=["uv", "pip"],
            description="Python packaging scenarios",
        )

        assert info.name == "packse"
        assert info.display_name == "Packse"
        assert "uv" in info.supported_pms
        assert "pip" in info.supported_pms

    def test_packse_info_constant(self):
        """Test predefined PACKSE_INFO constant."""
        assert PACKSE_INFO.name == "packse"
        assert "uv" in PACKSE_INFO.supported_pms
        assert "pip" in PACKSE_INFO.supported_pms


class TestProcessStatus:
    """Tests for ProcessStatus enum."""

    def test_process_status_values(self):
        """Test ProcessStatus enum values."""
        assert ProcessStatus.SUCCESS.value == "success"
        assert ProcessStatus.FAILED.value == "failed"
        assert ProcessStatus.TIMEOUT.value == "timeout"
        assert ProcessStatus.UNSATISFIABLE.value == "unsatisfiable"


class TestProcessScenarioResult:
    """Tests for ProcessScenarioResult dataclass."""

    def test_no_path_fields(self):
        """ProcessScenarioResult should not have path fields - files discovered by convention."""
        result = ProcessScenarioResult(
            pm_name="uv",
            status=ProcessStatus.SUCCESS,
            duration_seconds=1.5,
            exit_code=0,
        )
        # These fields should NOT exist - framework discovers files by convention
        assert not hasattr(result, "manifest_path")
        assert not hasattr(result, "lock_file_path")
        assert not hasattr(result, "sbom_path")
        assert not hasattr(result, "meta_path")

    def test_create_success_result(self):
        """Test creating a successful ProcessScenarioResult."""
        result = ProcessScenarioResult(
            pm_name="uv",
            status=ProcessStatus.SUCCESS,
            duration_seconds=1.5,
            exit_code=0,
        )

        assert result.pm_name == "uv"
        assert result.status == ProcessStatus.SUCCESS
        assert result.duration_seconds == 1.5
        assert result.exit_code == 0
        assert result.error_message is None

    def test_create_failed_result(self):
        """Test creating a failed ProcessScenarioResult."""
        result = ProcessScenarioResult(
            pm_name="uv",
            status=ProcessStatus.FAILED,
            duration_seconds=0.5,
            exit_code=1,
            error_message="Lock failed",
        )

        assert result.pm_name == "uv"
        assert result.status == ProcessStatus.FAILED
        assert result.exit_code == 1
        assert result.error_message == "Lock failed"

    def test_from_dict(self):
        """Test ProcessScenarioResult.from_dict() conversion."""
        data = {
            "pm_name": "uv",
            "status": "success",
            "duration_seconds": 1.5,
            "exit_code": 0,
        }

        result = ProcessScenarioResult.from_dict(data)

        assert result.pm_name == "uv"
        assert result.status == ProcessStatus.SUCCESS
        assert result.duration_seconds == 1.5
        assert result.exit_code == 0

    def test_from_dict_with_error(self):
        """Test from_dict with error message."""
        data = {
            "pm_name": "uv",
            "status": "failed",
            "duration_seconds": 0.5,
            "exit_code": 1,
            "error_message": "Failed",
        }

        result = ProcessScenarioResult.from_dict(data)

        assert result.pm_name == "uv"
        assert result.status == ProcessStatus.FAILED
        assert result.error_message == "Failed"


class TestPMInfo:
    """Tests for PMInfo dataclass."""

    def test_create_pminfo(self):
        """Test creating PMInfo."""
        info = PMInfo(
            name="uv",
            ecosystem="python",
            description="Fast Python package manager",
            supported_sources=["packse"],
            installed=True,
            version="0.5.11",
        )

        assert info.name == "uv"
        assert info.ecosystem == "python"
        assert info.supported_sources == ["packse"]
        assert info.installed is True
        assert info.version == "0.5.11"

    def test_pminfo_from_dict(self):
        """Test PMInfo.from_dict() with supported_sources."""
        data = {
            "name": "uv",
            "ecosystem": "python",
            "description": "Fast Python package manager",
            "supported_sources": ["packse"],
            "installed": True,
            "version": "0.5.11",
        }

        info = PMInfo.from_dict(data)

        assert info.name == "uv"
        assert info.ecosystem == "python"
        assert info.supported_sources == ["packse"]
        assert info.installed is True

    def test_pminfo_from_dict_defaults(self):
        """Test PMInfo.from_dict() with default values."""
        data = {
            "name": "pip",
            "ecosystem": "python",
            "description": "Python package installer",
            "supported_sources": ["pypi"],
        }

        info = PMInfo.from_dict(data)

        assert info.name == "pip"
        assert info.supported_sources == ["pypi"]
        assert info.installed is False  # Default value
        assert info.version is None  # Default value
