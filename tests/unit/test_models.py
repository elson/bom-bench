"""Tests for scenario models."""

from bom_bench.models.scenario import (
    Expected,
    ExpectedPackage,
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
