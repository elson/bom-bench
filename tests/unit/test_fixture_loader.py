from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bom_bench.fixtures.loader import FixtureSetLoader
from bom_bench.models.fixture import Fixture, FixtureSet, FixtureSetEnvironment


class TestFixtureSetLoader:
    @pytest.fixture
    def mock_pm(self):
        """Create a mock plugin manager."""
        return MagicMock()

    @pytest.fixture
    def sample_fixture_set_dict(self, tmp_path: Path):
        """Create a sample fixture set dict as would be returned by a plugin."""
        fixture_dir = tmp_path / "fixture1"
        fixture_dir.mkdir()
        (fixture_dir / "pyproject.toml").write_text('[project]\nname = "test"\n')
        (fixture_dir / "meta.json").write_text('{"satisfiable": true}')

        return {
            "name": "test-set",
            "description": "A test fixture set",
            "ecosystem": "python",
            "environment": {
                "tools": [
                    {"name": "uv", "version": "0.5.11"},
                    {"name": "python", "version": "3.12"},
                ],
                "env": {"UV_INDEX_URL": "http://localhost:3141"},
                "registry_url": "http://localhost:3141/simple-html",
            },
            "fixtures": [
                {
                    "name": "fixture1",
                    "files": {
                        "manifest": str(fixture_dir / "pyproject.toml"),
                        "lock_file": None,
                        "expected_sbom": None,
                        "meta": str(fixture_dir / "meta.json"),
                    },
                    "satisfiable": True,
                    "description": "First fixture",
                }
            ],
        }

    def test_loader_creation(self, mock_pm):
        loader = FixtureSetLoader(pm=mock_pm)
        assert loader.pm == mock_pm

    def test_loader_uses_default_pm(self):
        with patch("bom_bench.fixtures.loader.default_pm") as mock_default_pm:
            loader = FixtureSetLoader()
            assert loader.pm == mock_default_pm

    def test_load_all_returns_fixture_sets(self, mock_pm, sample_fixture_set_dict):
        mock_pm.hook.register_fixture_sets.return_value = [[sample_fixture_set_dict]]

        loader = FixtureSetLoader(pm=mock_pm)
        fixture_sets = loader.load_all()

        assert len(fixture_sets) == 1
        assert isinstance(fixture_sets[0], FixtureSet)
        assert fixture_sets[0].name == "test-set"

    def test_load_all_converts_environment(self, mock_pm, sample_fixture_set_dict):
        mock_pm.hook.register_fixture_sets.return_value = [[sample_fixture_set_dict]]

        loader = FixtureSetLoader(pm=mock_pm)
        fixture_sets = loader.load_all()

        env = fixture_sets[0].environment
        assert isinstance(env, FixtureSetEnvironment)
        assert len(env.tools) == 2
        assert env.tools[0].name == "uv"
        assert env.tools[0].version == "0.5.11"
        assert env.registry_url == "http://localhost:3141/simple-html"

    def test_load_all_converts_fixtures(self, mock_pm, sample_fixture_set_dict):
        mock_pm.hook.register_fixture_sets.return_value = [[sample_fixture_set_dict]]

        loader = FixtureSetLoader(pm=mock_pm)
        fixture_sets = loader.load_all()

        fixtures = fixture_sets[0].fixtures
        assert len(fixtures) == 1
        assert isinstance(fixtures[0], Fixture)
        assert fixtures[0].name == "fixture1"
        assert fixtures[0].satisfiable is True

    def test_load_all_empty_when_no_plugins(self, mock_pm):
        mock_pm.hook.register_fixture_sets.return_value = []

        loader = FixtureSetLoader(pm=mock_pm)
        fixture_sets = loader.load_all()

        assert fixture_sets == []

    def test_load_all_flattens_multiple_plugins(self, mock_pm, sample_fixture_set_dict, tmp_path):
        # Second fixture set from another plugin
        fixture_dir2 = tmp_path / "fixture2"
        fixture_dir2.mkdir()
        (fixture_dir2 / "pyproject.toml").write_text('[project]\nname = "test2"\n')
        (fixture_dir2 / "meta.json").write_text('{"satisfiable": false}')

        second_set = {
            "name": "another-set",
            "description": "Another set",
            "ecosystem": "python",
            "environment": {
                "tools": [],
                "env": {},
            },
            "fixtures": [
                {
                    "name": "fixture2",
                    "files": {
                        "manifest": str(fixture_dir2 / "pyproject.toml"),
                        "lock_file": None,
                        "expected_sbom": None,
                        "meta": str(fixture_dir2 / "meta.json"),
                    },
                    "satisfiable": False,
                }
            ],
        }

        # Simulate two plugins returning fixture sets
        mock_pm.hook.register_fixture_sets.return_value = [
            [sample_fixture_set_dict],
            [second_set],
        ]

        loader = FixtureSetLoader(pm=mock_pm)
        fixture_sets = loader.load_all()

        assert len(fixture_sets) == 2
        assert fixture_sets[0].name == "test-set"
        assert fixture_sets[1].name == "another-set"

    def test_load_by_name(self, mock_pm, sample_fixture_set_dict):
        mock_pm.hook.register_fixture_sets.return_value = [[sample_fixture_set_dict]]

        loader = FixtureSetLoader(pm=mock_pm)
        fixture_set = loader.load_by_name("test-set")

        assert fixture_set is not None
        assert fixture_set.name == "test-set"

    def test_load_by_name_not_found(self, mock_pm, sample_fixture_set_dict):
        mock_pm.hook.register_fixture_sets.return_value = [[sample_fixture_set_dict]]

        loader = FixtureSetLoader(pm=mock_pm)
        fixture_set = loader.load_by_name("nonexistent")

        assert fixture_set is None

    def test_load_by_ecosystem(self, mock_pm, sample_fixture_set_dict, tmp_path):
        # Create a JavaScript fixture set
        js_fixture_dir = tmp_path / "js-fixture"
        js_fixture_dir.mkdir()
        (js_fixture_dir / "package.json").write_text('{"name": "test"}')
        (js_fixture_dir / "meta.json").write_text('{"satisfiable": true}')

        js_set = {
            "name": "npm-set",
            "description": "JavaScript fixtures",
            "ecosystem": "javascript",
            "environment": {"tools": [], "env": {}},
            "fixtures": [
                {
                    "name": "js-fixture",
                    "files": {
                        "manifest": str(js_fixture_dir / "package.json"),
                        "lock_file": None,
                        "expected_sbom": None,
                        "meta": str(js_fixture_dir / "meta.json"),
                    },
                    "satisfiable": True,
                }
            ],
        }

        mock_pm.hook.register_fixture_sets.return_value = [[sample_fixture_set_dict, js_set]]

        loader = FixtureSetLoader(pm=mock_pm)

        python_sets = loader.load_by_ecosystem("python")
        assert len(python_sets) == 1
        assert python_sets[0].name == "test-set"

        js_sets = loader.load_by_ecosystem("javascript")
        assert len(js_sets) == 1
        assert js_sets[0].name == "npm-set"

    def test_get_fixture_set_names(self, mock_pm, sample_fixture_set_dict):
        mock_pm.hook.register_fixture_sets.return_value = [[sample_fixture_set_dict]]

        loader = FixtureSetLoader(pm=mock_pm)
        names = loader.get_fixture_set_names()

        assert names == ["test-set"]
