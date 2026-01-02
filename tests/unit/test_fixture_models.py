from pathlib import Path

from bom_bench.models.fixture import (
    Fixture,
    FixtureFiles,
    FixtureSet,
    FixtureSetEnvironment,
)
from bom_bench.sandbox.mise import ToolSpec


class TestFixtureSetEnvironment:
    def test_create_environment(self):
        env = FixtureSetEnvironment(
            tools=[ToolSpec(name="uv", version="0.5.11")],
            env_vars={"UV_INDEX_URL": "http://localhost:3141"},
        )
        assert len(env.tools) == 1
        assert env.tools[0].name == "uv"
        assert env.env_vars["UV_INDEX_URL"] == "http://localhost:3141"

    def test_environment_with_registry(self):
        env = FixtureSetEnvironment(
            tools=[],
            env_vars={},
            registry_url="http://localhost:3141/simple-html",
        )
        assert env.registry_url == "http://localhost:3141/simple-html"

    def test_environment_defaults(self):
        env = FixtureSetEnvironment(tools=[], env_vars={})
        assert env.registry_url is None


class TestFixtureFiles:
    def test_create_fixture_files(self, tmp_path: Path):
        manifest = tmp_path / "pyproject.toml"
        lock_file = tmp_path / "uv.lock"
        expected_sbom = tmp_path / "expected.cdx.json"
        meta = tmp_path / "meta.json"

        files = FixtureFiles(
            manifest=manifest,
            lock_file=lock_file,
            expected_sbom=expected_sbom,
            meta=meta,
        )

        assert files.manifest == manifest
        assert files.lock_file == lock_file
        assert files.expected_sbom == expected_sbom
        assert files.meta == meta

    def test_fixture_files_optional_fields(self, tmp_path: Path):
        manifest = tmp_path / "pyproject.toml"
        meta = tmp_path / "meta.json"

        files = FixtureFiles(
            manifest=manifest,
            lock_file=None,
            expected_sbom=None,
            meta=meta,
        )

        assert files.lock_file is None
        assert files.expected_sbom is None


class TestFixture:
    def test_create_fixture(self, tmp_path: Path):
        files = FixtureFiles(
            manifest=tmp_path / "pyproject.toml",
            lock_file=tmp_path / "uv.lock",
            expected_sbom=tmp_path / "expected.cdx.json",
            meta=tmp_path / "meta.json",
        )

        fixture = Fixture(
            name="fork-basic",
            files=files,
            satisfiable=True,
            description="A basic fork test scenario",
        )

        assert fixture.name == "fork-basic"
        assert fixture.satisfiable is True
        assert fixture.description == "A basic fork test scenario"
        assert fixture.files == files

    def test_fixture_default_description(self, tmp_path: Path):
        files = FixtureFiles(
            manifest=tmp_path / "pyproject.toml",
            lock_file=None,
            expected_sbom=None,
            meta=tmp_path / "meta.json",
        )

        fixture = Fixture(
            name="unsatisfiable-test",
            files=files,
            satisfiable=False,
        )

        assert fixture.description is None
        assert fixture.satisfiable is False

    def test_fixture_project_dir(self, tmp_path: Path):
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        manifest = project_dir / "pyproject.toml"

        files = FixtureFiles(
            manifest=manifest,
            lock_file=None,
            expected_sbom=None,
            meta=project_dir / "meta.json",
        )

        fixture = Fixture(name="test", files=files, satisfiable=True)

        assert fixture.project_dir == project_dir


class TestFixtureSet:
    def test_create_fixture_set(self, tmp_path: Path):
        env = FixtureSetEnvironment(
            tools=[
                ToolSpec(name="uv", version="0.5.11"),
                ToolSpec(name="python", version="3.12"),
            ],
            env_vars={"UV_INDEX_URL": "http://localhost:3141/simple"},
            registry_url="http://localhost:3141/simple-html",
        )

        files = FixtureFiles(
            manifest=tmp_path / "pyproject.toml",
            lock_file=tmp_path / "uv.lock",
            expected_sbom=tmp_path / "expected.cdx.json",
            meta=tmp_path / "meta.json",
        )

        fixture = Fixture(name="test-fixture", files=files, satisfiable=True)

        fixture_set = FixtureSet(
            name="packse",
            description="Python dependency resolution test scenarios",
            ecosystem="python",
            environment=env,
            fixtures=[fixture],
        )

        assert fixture_set.name == "packse"
        assert fixture_set.ecosystem == "python"
        assert len(fixture_set.fixtures) == 1
        assert fixture_set.fixtures[0].name == "test-fixture"
        assert fixture_set.environment.registry_url == "http://localhost:3141/simple-html"

    def test_fixture_set_multiple_fixtures(self, tmp_path: Path):
        env = FixtureSetEnvironment(tools=[], env_vars={})

        fixtures = []
        for i in range(5):
            fixture_dir = tmp_path / f"fixture-{i}"
            fixture_dir.mkdir()
            files = FixtureFiles(
                manifest=fixture_dir / "pyproject.toml",
                lock_file=fixture_dir / "uv.lock",
                expected_sbom=fixture_dir / "expected.cdx.json",
                meta=fixture_dir / "meta.json",
            )
            fixtures.append(Fixture(name=f"fixture-{i}", files=files, satisfiable=True))

        fixture_set = FixtureSet(
            name="test-set",
            description="Test fixture set",
            ecosystem="python",
            environment=env,
            fixtures=fixtures,
        )

        assert len(fixture_set.fixtures) == 5
        assert fixture_set.fixtures[2].name == "fixture-2"

    def test_fixture_set_from_dict(self, tmp_path: Path):
        fixture_dir = tmp_path / "test"
        fixture_dir.mkdir()

        data = {
            "name": "packse",
            "description": "Packse fixtures",
            "ecosystem": "python",
            "environment": {
                "tools": [
                    {"name": "uv", "version": "0.5.11"},
                    {"name": "python", "version": "3.12"},
                ],
                "env_vars": {"UV_INDEX_URL": "http://localhost:3141"},
                "registry_url": "http://localhost:3141/simple-html",
            },
            "fixtures": [
                {
                    "name": "fork-basic",
                    "files": {
                        "manifest": str(fixture_dir / "pyproject.toml"),
                        "lock_file": str(fixture_dir / "uv.lock"),
                        "expected_sbom": str(fixture_dir / "expected.cdx.json"),
                        "meta": str(fixture_dir / "meta.json"),
                    },
                    "satisfiable": True,
                    "description": "A test",
                }
            ],
        }

        fixture_set = FixtureSet.from_dict(data)

        assert fixture_set.name == "packse"
        assert fixture_set.ecosystem == "python"
        assert len(fixture_set.environment.tools) == 2
        assert fixture_set.environment.tools[0].name == "uv"
        assert len(fixture_set.fixtures) == 1
        assert fixture_set.fixtures[0].name == "fork-basic"
