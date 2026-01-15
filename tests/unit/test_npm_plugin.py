"""Tests for the npm fixture set plugin."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from bom_bench.fixtures.npm import (
    _clone_npm_cli,
    _compute_source_hash,
    _extract_packages_from_lock,
    _generate_expected_sbom,
    _is_cache_valid,
    _load_cached_fixtures,
    _load_fixtures,
    _save_cache_manifest,
    register_fixture_sets,
)
from bom_bench.fixtures.npm.arborist_parser import (
    ResolvedPackage,
    _extract_string_value,
    _extract_test_name,
    _parse_arborist_content,
    _split_exports,
    parse_snapshot_file,
)


class TestArboristParser:
    def test_extract_test_name(self):
        key = "test/arborist/reify.js TAP testing-peer-deps package > expect resolving Promise 1"
        name = _extract_test_name(key)
        assert name == "testing-peer-deps package"

    def test_extract_test_name_invalid(self):
        assert _extract_test_name("invalid key") is None
        assert _extract_test_name("test/arborist/reify.js TAP no marker") is None

    def test_extract_string_value(self):
        line = '  "name": "lodash",'
        assert _extract_string_value(line) == "lodash"

        line = '  "version": "4.17.21",'
        assert _extract_string_value(line) == "4.17.21"

    def test_extract_string_value_no_match(self):
        assert _extract_string_value("no colon quote") is None
        assert _extract_string_value('incomplete: "value') is None

    def test_parse_arborist_content(self):
        content = """
        ArboristNode {
            "name": "lodash",
            "version": "4.17.21",
            "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
        }
        ArboristNode {
            "name": "express",
            "version": "4.18.2",
            "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
        }
        """
        packages = _parse_arborist_content(content)

        assert len(packages) == 2
        assert packages[0].name == "lodash"
        assert packages[0].version == "4.17.21"
        assert "registry.npmjs.org" in packages[0].resolved
        assert packages[1].name == "express"

    def test_parse_arborist_content_filters_non_registry(self):
        content = """
        "name": "local-pkg",
        "version": "1.0.0",
        "resolved": "file:../local-pkg",
        """
        packages = _parse_arborist_content(content)
        assert len(packages) == 0

    def test_split_exports(self):
        content = """exports[`test 1`] = `
line 1
line 2
`

exports[`test 2`] = `
content
`"""
        exports = _split_exports(content)

        assert "test 1" in exports
        assert "line 1\nline 2" in exports["test 1"]
        assert "test 2" in exports
        assert "content" in exports["test 2"]

    def test_parse_snapshot_file(self, tmp_path: Path):
        snapshot_content = """exports[`test/arborist/reify.js TAP test-case > expect resolving Promise 1`] = `
ArboristNode {
    "name": "lodash",
    "version": "4.17.21",
    "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
}
`"""
        snapshot_file = tmp_path / "snapshot.cjs"
        snapshot_file.write_text(snapshot_content)

        results = parse_snapshot_file(snapshot_file)

        assert "test-case" in results
        assert len(results["test-case"]) == 1
        assert results["test-case"][0].name == "lodash"


class TestNpmPlugin:
    def test_compute_source_hash(self, tmp_path: Path):
        test_dir = tmp_path / "workspaces/arborist/test/arborist"
        test_dir.mkdir(parents=True)
        test_file = test_dir / "reify.js"
        test_file.write_text("test content")

        snapshot_dir = tmp_path / "workspaces/arborist/tap-snapshots/test/arborist"
        snapshot_dir.mkdir(parents=True)
        snapshot_file = snapshot_dir / "reify.js.test.cjs"
        snapshot_file.write_text("snapshot")

        hash1 = _compute_source_hash(tmp_path)
        assert len(hash1) == 16

        # Changing test file should change hash
        test_file.write_text("modified test content")
        hash2 = _compute_source_hash(tmp_path)
        assert hash1 != hash2

        # Changing snapshot should also change hash
        snapshot_file.write_text("modified snapshot")
        hash3 = _compute_source_hash(tmp_path)
        assert hash2 != hash3

    def test_is_cache_valid_no_manifest(self, tmp_path: Path):
        assert not _is_cache_valid(tmp_path, "somehash")

    def test_is_cache_valid_matching_hash(self, tmp_path: Path):
        manifest = tmp_path / ".cache_manifest.json"
        manifest.write_text(json.dumps({"hash": "abcd1234"}))

        assert _is_cache_valid(tmp_path, "abcd1234")
        assert not _is_cache_valid(tmp_path, "different")

    def test_is_cache_valid_invalid_json(self, tmp_path: Path):
        manifest = tmp_path / ".cache_manifest.json"
        manifest.write_text("invalid json")

        assert not _is_cache_valid(tmp_path, "anyhash")

    def test_save_cache_manifest(self, tmp_path: Path):
        _save_cache_manifest(tmp_path, "testhash123")

        manifest = tmp_path / ".cache_manifest.json"
        assert manifest.exists()

        data = json.loads(manifest.read_text())
        assert data["hash"] == "testhash123"

    def test_load_cached_fixtures(self, tmp_path: Path):
        fixture1 = tmp_path / "fixture1"
        fixture1.mkdir()
        (fixture1 / "package.json").write_text("{}")
        (fixture1 / "expected.cdx.json").write_text("{}")
        (fixture1 / "meta.json").write_text("{}")

        fixture2 = tmp_path / "fixture2"
        fixture2.mkdir()
        (fixture2 / "package.json").write_text("{}")
        (fixture2 / "package-lock.json").write_text("{}")
        (fixture2 / "expected.cdx.json").write_text("{}")
        (fixture2 / "meta.json").write_text("{}")

        fixtures = _load_cached_fixtures(tmp_path)

        assert len(fixtures) == 2
        assert fixtures[0]["name"] == "fixture1"
        assert "lock_file" not in fixtures[0]["files"]
        assert fixtures[1]["name"] == "fixture2"
        assert "lock_file" in fixtures[1]["files"]

    def test_load_cached_fixtures_skips_hidden(self, tmp_path: Path):
        hidden = tmp_path / ".hidden"
        hidden.mkdir()

        fixtures = _load_cached_fixtures(tmp_path)
        assert len(fixtures) == 0

    def test_load_cached_fixtures_skips_no_meta(self, tmp_path: Path):
        no_meta = tmp_path / "no-meta"
        no_meta.mkdir()
        (no_meta / "package.json").write_text("{}")

        fixtures = _load_cached_fixtures(tmp_path)
        assert len(fixtures) == 0

    def test_extract_packages_from_lock(self):
        lock_data = {
            "lockfileVersion": 3,
            "dependencies": {
                "express": {
                    "version": "4.18.2",
                    "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
                    "integrity": "sha512-...",
                },
                "lodash": {
                    "version": "4.17.21",
                    "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
                },
                "local-dep": {
                    "version": "file:../local",
                    "resolved": "file:../local",
                },
            },
        }

        packages = _extract_packages_from_lock(lock_data)

        assert len(packages) == 2
        assert packages[0].name == "express"
        assert packages[0].version == "4.18.2"
        assert packages[1].name == "lodash"
        assert packages[1].version == "4.17.21"

    def test_extract_packages_from_lock_empty(self):
        lock_data = {"lockfileVersion": 3, "dependencies": {}}

        packages = _extract_packages_from_lock(lock_data)

        assert len(packages) == 0

    def test_generate_expected_sbom(self, tmp_path: Path):
        mock_bom_bench = Mock()
        mock_bom_bench.generate_sbom_file = Mock()
        packages = [
            ResolvedPackage("lodash", "4.17.21", "https://registry.npmjs.org/lodash"),
            ResolvedPackage("express", "4.18.2", "https://registry.npmjs.org/express"),
        ]
        sbom_path = tmp_path / "expected.cdx.json"

        _generate_expected_sbom(mock_bom_bench, "test-fixture", packages, sbom_path)

        mock_bom_bench.generate_sbom_file.assert_called_once()
        call_args = mock_bom_bench.generate_sbom_file.call_args
        # Check positional arguments
        assert call_args[0][0] == "test-fixture"  # scenario_name
        assert call_args[0][1] == sbom_path  # output_path
        pkg_list = call_args[0][2]  # packages
        assert len(pkg_list) == 2
        assert pkg_list[0]["purl_type"] == "npm"
        assert pkg_list[0]["name"] == "lodash"
        assert pkg_list[1]["name"] == "express"

    def test_clone_npm_cli_not_exists(self, tmp_path: Path):
        mock_logger = Mock()
        npm_cli_dir = tmp_path / "npm-cli"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="")
            _clone_npm_cli(mock_logger, npm_cli_dir)

            assert mock_run.called
            clone_call = [c for c in mock_run.call_args_list if "clone" in str(c)]
            assert len(clone_call) == 1

    def test_clone_npm_cli_exists_correct_tag(self, tmp_path: Path):
        mock_logger = Mock()
        npm_cli_dir = tmp_path / "npm-cli"
        npm_cli_dir.mkdir()
        (npm_cli_dir / ".git").mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="v10.9.2\n")
            result = _clone_npm_cli(mock_logger, npm_cli_dir)

            assert result == npm_cli_dir
            assert mock_run.call_count >= 1
            for call in mock_run.call_args_list:
                args = call[0][0] if call[0] else []
                assert "clone" not in args

    def test_register_fixture_sets(self, tmp_path: Path):
        mock_bom_bench = Mock()
        mock_logger = Mock()
        mock_bom_bench.get_logger = Mock(return_value=mock_logger)

        with patch("bom_bench.fixtures.npm._load_fixtures", return_value=[]) as mock_load:
            result = register_fixture_sets(mock_bom_bench, tmp_path)

            assert len(result) == 1
            assert result[0]["name"] == "npm"
            assert result[0]["ecosystem"] == "javascript"
            assert len(result[0]["environment"]["tools"]) == 1
            mock_load.assert_called_once()

    def test_load_fixtures_uses_cache(self, tmp_path: Path):
        mock_bom_bench = Mock()
        mock_logger = Mock()
        npm_cli_dir = tmp_path / "npm-cli"
        cache_dir = tmp_path / "cache"

        cache_dir.mkdir()
        manifest = cache_dir / ".cache_manifest.json"
        manifest.write_text(json.dumps({"hash": "matchinghash"}))

        fixture_dir = cache_dir / "test-fixture"
        fixture_dir.mkdir()
        (fixture_dir / "package.json").write_text("{}")
        (fixture_dir / "expected.cdx.json").write_text("{}")
        (fixture_dir / "meta.json").write_text("{}")

        with (
            patch("bom_bench.fixtures.npm._clone_npm_cli", return_value=npm_cli_dir),
            patch("bom_bench.fixtures.npm._compute_source_hash", return_value="matchinghash"),
        ):
            fixtures = _load_fixtures(mock_bom_bench, mock_logger, npm_cli_dir, cache_dir)

        assert len(fixtures) == 1
        assert fixtures[0]["name"] == "test-fixture"
