"""Tests for the packse fixture set plugin."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bom_bench.fixtures.packse import (
    _compute_cache_hash,
    _generate_fixture,
    _generate_fixtures,
    _generate_pyproject_toml,
    _load_cache_manifest,
    _load_cached_fixtures,
    _parse_uv_lock,
    _save_cache_manifest,
    _should_include_scenario,
    register_fixture_sets,
)


class TestGeneratePyprojectToml:
    def test_basic_project(self):
        content = _generate_pyproject_toml(
            name="test-project",
            version="1.0.0",
            dependencies=["requests>=2.0"],
        )
        assert "[project]" in content
        assert 'name = "test-project"' in content
        assert 'version = "1.0.0"' in content
        assert '"requests>=2.0"' in content

    def test_empty_dependencies(self):
        content = _generate_pyproject_toml(
            name="empty",
            version="0.1.0",
            dependencies=[],
        )
        assert "dependencies = []" in content

    def test_with_requires_python(self):
        content = _generate_pyproject_toml(
            name="py312",
            version="1.0.0",
            dependencies=[],
            requires_python=">=3.12",
        )
        assert 'requires-python = ">=3.12"' in content

    def test_with_required_environments(self):
        content = _generate_pyproject_toml(
            name="multi-env",
            version="1.0.0",
            dependencies=[],
            required_environments=["sys_platform == 'linux'"],
        )
        assert "[tool.uv]" in content
        assert "required-environments" in content
        assert "sys_platform == 'linux'" in content


class TestParseUvLock:
    def test_parse_valid_lock(self, tmp_path: Path):
        lock_content = """
version = 1
requires-python = ">=3.12"

[[package]]
name = "requests"
version = "2.31.0"

[[package]]
name = "urllib3"
version = "2.0.0"
"""
        lock_file = tmp_path / "uv.lock"
        lock_file.write_text(lock_content)

        packages = _parse_uv_lock(lock_file)

        assert len(packages) == 2
        assert {"name": "requests", "version": "2.31.0"} in packages
        assert {"name": "urllib3", "version": "2.0.0"} in packages

    def test_parse_excludes_virtual_root(self, tmp_path: Path):
        lock_content = """
version = 1

[[package]]
name = "project"
version = "0.1.0"
source = { virtual = "." }

[[package]]
name = "requests"
version = "2.31.0"
"""
        lock_file = tmp_path / "uv.lock"
        lock_file.write_text(lock_content)

        packages = _parse_uv_lock(lock_file)

        assert len(packages) == 1
        assert packages[0]["name"] == "requests"

    def test_parse_nonexistent_file(self, tmp_path: Path):
        packages = _parse_uv_lock(tmp_path / "nonexistent.lock")
        assert packages == []

    def test_parse_empty_lock(self, tmp_path: Path):
        lock_file = tmp_path / "uv.lock"
        lock_file.write_text("version = 1")

        packages = _parse_uv_lock(lock_file)
        assert packages == []


class TestComputeCacheHash:
    def test_hash_changes_with_content(self, tmp_path: Path):
        toml_file = tmp_path / "test.toml"
        toml_file.write_text("content1")

        hash1 = _compute_cache_hash(tmp_path)

        toml_file.write_text("content2")
        hash2 = _compute_cache_hash(tmp_path)

        assert hash1 != hash2

    def test_hash_consistent(self, tmp_path: Path):
        toml_file = tmp_path / "test.toml"
        toml_file.write_text("consistent content")

        hash1 = _compute_cache_hash(tmp_path)
        hash2 = _compute_cache_hash(tmp_path)

        assert hash1 == hash2

    def test_hash_includes_nested_files(self, tmp_path: Path):
        nested = tmp_path / "nested"
        nested.mkdir()
        (nested / "file.toml").write_text("nested content")

        hash_with_nested = _compute_cache_hash(tmp_path)

        (nested / "file.toml").write_text("different")
        hash_changed = _compute_cache_hash(tmp_path)

        assert hash_with_nested != hash_changed


class TestCacheManifest:
    def test_save_and_load_manifest(self, tmp_path: Path):
        test_hash = "abc123def456"

        _save_cache_manifest(tmp_path, test_hash)
        manifest = _load_cache_manifest(tmp_path)

        assert manifest is not None
        assert manifest["source_hash"] == test_hash

    def test_load_nonexistent_manifest(self, tmp_path: Path):
        manifest = _load_cache_manifest(tmp_path)
        assert manifest is None

    def test_manifest_overwrites(self, tmp_path: Path):
        _save_cache_manifest(tmp_path, "hash1")
        _save_cache_manifest(tmp_path, "hash2")

        manifest = _load_cache_manifest(tmp_path)
        assert manifest["source_hash"] == "hash2"


class TestShouldIncludeScenario:
    def test_includes_universal_scenario(self):
        scenario = {
            "name": "test-scenario",
            "resolver_options": {"universal": True},
        }
        assert _should_include_scenario(scenario, []) is True

    def test_excludes_non_universal_scenario(self):
        scenario = {
            "name": "test-scenario",
            "resolver_options": {"universal": False},
        }
        assert _should_include_scenario(scenario, []) is False

    def test_excludes_missing_universal(self):
        scenario = {
            "name": "test-scenario",
            "resolver_options": {},
        }
        assert _should_include_scenario(scenario, []) is False

    def test_excludes_pattern_match(self):
        scenario = {
            "name": "example-scenario",
            "resolver_options": {"universal": True},
        }
        assert _should_include_scenario(scenario, ["example"]) is False

    def test_excludes_pattern_case_insensitive(self):
        scenario = {
            "name": "EXAMPLE-TEST",
            "resolver_options": {"universal": True},
        }
        assert _should_include_scenario(scenario, ["example"]) is False

    def test_includes_no_pattern_match(self):
        scenario = {
            "name": "real-scenario",
            "resolver_options": {"universal": True},
        }
        assert _should_include_scenario(scenario, ["example", "test"]) is True


class TestLoadCachedFixtures:
    def test_load_fixtures_from_cache(self, tmp_path: Path):
        fixture_dir = tmp_path / "test-fixture"
        fixture_dir.mkdir()
        (fixture_dir / "pyproject.toml").write_text('[project]\nname = "test"')
        (fixture_dir / "uv.lock").write_text("version = 1")
        (fixture_dir / "expected.cdx.json").write_text("{}")
        (fixture_dir / "meta.json").write_text('{"satisfiable": true}')

        fixtures = _load_cached_fixtures(tmp_path)

        assert len(fixtures) == 1
        assert fixtures[0]["name"] == "test-fixture"
        assert fixtures[0]["satisfiable"] is True
        assert fixtures[0]["files"]["manifest"].endswith("pyproject.toml")
        assert fixtures[0]["files"]["lock_file"].endswith("uv.lock")
        assert fixtures[0]["files"]["expected_sbom"].endswith("expected.cdx.json")

    def test_skip_hidden_directories(self, tmp_path: Path):
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "meta.json").write_text('{"satisfiable": true}')

        fixture_dir = tmp_path / "visible"
        fixture_dir.mkdir()
        (fixture_dir / "pyproject.toml").write_text('[project]\nname = "test"')
        (fixture_dir / "meta.json").write_text('{"satisfiable": true}')

        fixtures = _load_cached_fixtures(tmp_path)

        assert len(fixtures) == 1
        assert fixtures[0]["name"] == "visible"

    def test_skip_directories_without_meta(self, tmp_path: Path):
        no_meta_dir = tmp_path / "no-meta"
        no_meta_dir.mkdir()
        (no_meta_dir / "pyproject.toml").write_text('[project]\nname = "test"')

        with_meta_dir = tmp_path / "with-meta"
        with_meta_dir.mkdir()
        (with_meta_dir / "pyproject.toml").write_text('[project]\nname = "test"')
        (with_meta_dir / "meta.json").write_text('{"satisfiable": false}')

        fixtures = _load_cached_fixtures(tmp_path)

        assert len(fixtures) == 1
        assert fixtures[0]["name"] == "with-meta"

    def test_handles_unsatisfiable_fixture(self, tmp_path: Path):
        fixture_dir = tmp_path / "unsatisfiable"
        fixture_dir.mkdir()
        (fixture_dir / "pyproject.toml").write_text('[project]\nname = "test"')
        (fixture_dir / "meta.json").write_text('{"satisfiable": false}')

        fixtures = _load_cached_fixtures(tmp_path)

        assert len(fixtures) == 1
        assert fixtures[0]["satisfiable"] is False
        assert fixtures[0]["files"]["lock_file"] is None
        assert fixtures[0]["files"]["expected_sbom"] is None

    def test_empty_cache_dir(self, tmp_path: Path):
        fixtures = _load_cached_fixtures(tmp_path)
        assert fixtures == []


class TestGenerateFixture:
    @pytest.fixture
    def mock_bom_bench(self):
        """Create a mock bom_bench module."""
        mock = MagicMock()
        mock.get_logger.return_value = MagicMock()
        mock.generate_meta_file = MagicMock()
        mock.generate_sbom_file = MagicMock()
        return mock

    @pytest.fixture
    def sample_scenario(self):
        return {
            "name": "test-scenario",
            "root": {
                "requires": [{"requirement": "requests>=2.0"}],
                "requires_python": ">=3.12",
            },
            "resolver_options": {
                "universal": True,
                "required_environments": None,
            },
            "description": "A test scenario",
        }

    def test_generate_satisfiable_fixture(self, tmp_path: Path, mock_bom_bench, sample_scenario):
        with patch("bom_bench.fixtures.packse.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            lock_file = tmp_path / "test-scenario" / "uv.lock"

            def create_lock(*args, **kwargs):
                lock_file.parent.mkdir(parents=True, exist_ok=True)
                lock_file.write_text('[[package]]\nname = "requests"\nversion = "2.31.0"')
                return MagicMock(returncode=0, stdout="", stderr="")

            mock_run.side_effect = create_lock

            result = _generate_fixture(sample_scenario, tmp_path, mock_bom_bench)

            assert result is not None
            assert result["name"] == "test-scenario"
            assert result["satisfiable"] is True
            assert result["description"] == "A test scenario"
            assert "pyproject.toml" in result["files"]["manifest"]

    def test_generate_unsatisfiable_fixture(self, tmp_path: Path, mock_bom_bench, sample_scenario):
        with patch("bom_bench.fixtures.packse.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="No solution found")

            result = _generate_fixture(sample_scenario, tmp_path, mock_bom_bench)

            assert result is not None
            assert result["satisfiable"] is False

    def test_generate_fixture_timeout(self, tmp_path: Path, mock_bom_bench, sample_scenario):
        with patch("bom_bench.fixtures.packse.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="uv lock", timeout=120)

            result = _generate_fixture(sample_scenario, tmp_path, mock_bom_bench, timeout=120)

            assert result is not None
            assert result["satisfiable"] is False

    def test_generate_fixture_uv_not_found(self, tmp_path: Path, mock_bom_bench, sample_scenario):
        with patch("bom_bench.fixtures.packse.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("uv not found")

            result = _generate_fixture(sample_scenario, tmp_path, mock_bom_bench)

            assert result is None


class TestGenerateFixtures:
    @pytest.fixture
    def mock_bom_bench(self):
        mock = MagicMock()
        mock.get_logger.return_value = MagicMock()
        mock.generate_meta_file = MagicMock()
        mock.generate_sbom_file = MagicMock()
        return mock

    def test_uses_cache_when_valid(self, tmp_path: Path, mock_bom_bench):
        data_dir = tmp_path / "data"
        cache_dir = tmp_path / "cache"
        data_dir.mkdir()
        cache_dir.mkdir()

        (data_dir / "scenario.toml").write_text("test data")

        source_hash = _compute_cache_hash(data_dir)
        _save_cache_manifest(cache_dir, source_hash)

        fixture_dir = cache_dir / "cached-fixture"
        fixture_dir.mkdir()
        (fixture_dir / "pyproject.toml").write_text('[project]\nname = "test"')
        (fixture_dir / "meta.json").write_text('{"satisfiable": true}')

        fixtures = _generate_fixtures(mock_bom_bench, data_dir, cache_dir)

        assert len(fixtures) == 1
        assert fixtures[0]["name"] == "cached-fixture"

    def test_regenerates_when_hash_differs(self, tmp_path: Path, mock_bom_bench):
        data_dir = tmp_path / "data"
        cache_dir = tmp_path / "cache"
        data_dir.mkdir()
        cache_dir.mkdir()

        (data_dir / "scenario.toml").write_text("test data")
        _save_cache_manifest(cache_dir, "old-hash")

        with (
            patch("packse.fetch.fetch"),
            patch("packse.inspect.find_scenario_files") as mock_find,
            patch("packse.inspect.variables_for_templates") as mock_vars,
        ):
            # Return empty list - function returns early with []
            mock_find.return_value = []
            mock_vars.return_value = {"scenarios": []}

            fixtures = _generate_fixtures(mock_bom_bench, data_dir, cache_dir)

            # Verify regeneration was attempted (find_scenario_files called)
            assert fixtures == []
            mock_find.assert_called_once_with(data_dir)

    def test_regenerates_with_scenarios(self, tmp_path: Path, mock_bom_bench):
        data_dir = tmp_path / "data"
        cache_dir = tmp_path / "cache"
        data_dir.mkdir()
        cache_dir.mkdir()

        (data_dir / "scenario.toml").write_text("test data")
        _save_cache_manifest(cache_dir, "old-hash")

        mock_scenario_file = MagicMock()

        with (
            patch("packse.fetch.fetch"),
            patch("packse.inspect.find_scenario_files") as mock_find,
            patch("packse.inspect.variables_for_templates") as mock_vars,
        ):
            mock_find.return_value = [mock_scenario_file]
            mock_vars.return_value = {"scenarios": []}

            fixtures = _generate_fixtures(mock_bom_bench, data_dir, cache_dir)

            assert fixtures == []
            mock_vars.assert_called_once()


class TestRegisterFixtureSets:
    def test_returns_fixture_set_structure(self):
        with (
            patch("bom_bench.fixtures.packse._generate_fixtures") as mock_gen,
            patch("bom_bench.config.DATA_DIR", Path("/mock/data")),
        ):
            mock_gen.return_value = [
                {
                    "name": "test-fixture",
                    "files": {},
                    "satisfiable": True,
                }
            ]

            mock_bom_bench = MagicMock()
            result = register_fixture_sets(mock_bom_bench)

            assert len(result) == 1
            fixture_set = result[0]
            assert fixture_set["name"] == "packse"
            assert fixture_set["ecosystem"] == "python"
            assert "environment" in fixture_set
            assert fixture_set["environment"]["tools"][0]["name"] == "uv"
            assert fixture_set["fixtures"] == mock_gen.return_value
