"""Tests for the npm fixture set plugin."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from bom_bench.fixtures.npm import (
    _clone_npm_cli,
    _compute_source_hash,
    _generate_expected_sbom,
    _is_cache_valid,
    _load_cached_fixtures,
    _load_fixtures,
    _process_fixture,
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
from bom_bench.fixtures.npm.js_parser import (
    _parse_value,
    create_js_parser,
    get_node_text,
    parse_fixture_test_mapping,
    parse_reify_case,
)


class TestJsParser:
    def test_create_js_parser(self):
        parser = create_js_parser()
        assert parser is not None

    def test_get_node_text(self):
        parser = create_js_parser()
        source = b'const x = "hello";'
        tree = parser.parse(source)
        node = tree.root_node
        text = get_node_text(node, source)
        assert text == 'const x = "hello";'

    def test_parse_reify_case_basic(self, tmp_path: Path):
        js_content = """
        const t = require('tap')
        t.test('test name', async t => {
            const dir = t.testdir({
                'package.json': JSON.stringify({
                    name: 'test-pkg',
                    version: '1.0.0',
                    dependencies: {
                        lodash: '^4.17.0'
                    }
                })
            })
        })
        """
        js_file = tmp_path / "test-case.js"
        js_file.write_text(js_content)

        result = parse_reify_case(js_file)

        assert result is not None
        assert result["name"] == "test-case"
        assert result["package_json"]["name"] == "test-pkg"
        assert result["package_json"]["version"] == "1.0.0"
        assert result["package_lock"] is None

    def test_parse_reify_case_with_lock(self, tmp_path: Path):
        js_content = """
        t.testdir({
            'package.json': JSON.stringify({
                name: 'test',
                version: '1.0.0'
            }),
            'package-lock.json': JSON.stringify({
                lockfileVersion: 3,
                packages: {}
            })
        })
        """
        js_file = tmp_path / "with-lock.js"
        js_file.write_text(js_content)

        result = parse_reify_case(js_file)

        assert result is not None
        assert result["package_json"] is not None
        assert result["package_lock"] is not None
        assert result["package_lock"]["lockfileVersion"] == 3

    def test_parse_reify_case_no_package_json(self, tmp_path: Path):
        js_content = "const x = 42;"
        js_file = tmp_path / "invalid.js"
        js_file.write_text(js_content)

        result = parse_reify_case(js_file)

        assert result is None

    def test_parse_value_string(self):
        parser = create_js_parser()
        source = b'const x = "hello world";'
        tree = parser.parse(source)

        def find_node(node, node_type):
            if node.type == node_type:
                return node
            for child in node.children:
                result = find_node(child, node_type)
                if result:
                    return result
            return None

        string_node = find_node(tree.root_node, "string")
        assert string_node is not None
        value = _parse_value(string_node, source)
        assert value == "hello world"

    def test_parse_value_number(self):
        parser = create_js_parser()
        source = b"const x = 42;"
        tree = parser.parse(source)

        def find_node(node, node_type):
            if node.type == node_type:
                return node
            for child in node.children:
                result = find_node(child, node_type)
                if result:
                    return result
            return None

        number_node = find_node(tree.root_node, "number")
        assert number_node is not None
        value = _parse_value(number_node, source)
        assert value == 42

    def test_parse_value_boolean(self):
        parser = create_js_parser()
        source = b"const x = true;"
        tree = parser.parse(source)

        def find_node(node, node_type):
            if node.type == node_type:
                return node
            for child in node.children:
                result = find_node(child, node_type)
                if result:
                    return result
            return None

        true_node = find_node(tree.root_node, "true")
        assert true_node is not None
        assert _parse_value(true_node, source) is True

        source = b"const y = false;"
        tree = parser.parse(source)
        false_node = find_node(tree.root_node, "false")
        assert false_node is not None
        assert _parse_value(false_node, source) is False

    def test_parse_value_null(self):
        parser = create_js_parser()
        source = b"const x = null;"
        tree = parser.parse(source)

        def find_node(node, node_type):
            if node.type == node_type:
                return node
            for child in node.children:
                result = find_node(child, node_type)
                if result:
                    return result
            return None

        null_node = find_node(tree.root_node, "null")
        assert null_node is not None
        assert _parse_value(null_node, source) is None

    def test_parse_fixture_test_mapping(self, tmp_path: Path):
        test_content = """
        t.test('basic test', async t => {
            const dir = fixture(t, 'basic-fixture')
        })
        t.test('another test', async t => {
            fixture(t, 'another-fixture')
        })
        """
        test_file = tmp_path / "reify.js"
        test_file.write_text(test_content)

        mapping = parse_fixture_test_mapping(test_file)

        assert mapping.get("basic-fixture") == "basic test"
        assert mapping.get("another-fixture") == "another test"


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
        reify_cases = tmp_path / "workspaces/arborist/test/fixtures/reify-cases"
        reify_cases.mkdir(parents=True)
        (reify_cases / "test1.js").write_text("content1")
        (reify_cases / "test2.js").write_text("content2")

        snapshot_dir = tmp_path / "workspaces/arborist/tap-snapshots/test/arborist"
        snapshot_dir.mkdir(parents=True)
        snapshot_file = snapshot_dir / "reify.js.test.cjs"
        snapshot_file.write_text("snapshot")

        hash1 = _compute_source_hash(tmp_path)
        assert len(hash1) == 16

        (reify_cases / "test3.js").write_text("content3")
        hash2 = _compute_source_hash(tmp_path)
        assert hash1 != hash2

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

    def test_process_fixture_skip_malformed(self, tmp_path: Path):
        case_file = tmp_path / "malformed-json.js"
        case_file.write_text("")

        result = _process_fixture(case_file, {}, {}, Mock(), Mock(), tmp_path)

        assert result is None

    def test_process_fixture_skip_fail(self, tmp_path: Path):
        case_file = tmp_path / "test-fail.js"
        case_file.write_text("")

        result = _process_fixture(case_file, {}, {}, Mock(), Mock(), tmp_path)

        assert result is None

    def test_process_fixture_no_package_json(self, tmp_path: Path):
        case_file = tmp_path / "valid-name.js"
        case_file.write_text("const x = 1;")

        with patch("bom_bench.fixtures.npm.parse_reify_case", return_value=None):
            result = _process_fixture(case_file, {}, {}, Mock(), Mock(), tmp_path)

        assert result is None

    def test_process_fixture_no_snapshot(self, tmp_path: Path):
        case_file = tmp_path / "no-snapshot.js"
        case_file.write_text("")
        mock_logger = Mock()

        parsed = {"name": "no-snapshot", "package_json": {"name": "test"}, "package_lock": None}

        with patch("bom_bench.fixtures.npm.parse_reify_case", return_value=parsed):
            result = _process_fixture(case_file, {}, {}, Mock(), mock_logger, tmp_path)

        assert result is None

    def test_process_fixture_success(self, tmp_path: Path):
        case_file = tmp_path / "success.js"
        case_file.write_text("")
        mock_logger = Mock()
        mock_bom_bench = Mock()
        mock_bom_bench.generate_sbom_file = Mock()
        cache_dir = tmp_path / "cache"

        parsed = {
            "name": "success",
            "package_json": {"name": "test", "version": "1.0.0"},
            "package_lock": None,
        }
        packages = [ResolvedPackage("lodash", "4.17.21", "https://registry.npmjs.org/lodash")]

        with patch("bom_bench.fixtures.npm.parse_reify_case", return_value=parsed):
            result = _process_fixture(
                case_file,
                {"success": "success test"},
                {"success test": packages},
                mock_bom_bench,
                mock_logger,
                cache_dir,
            )

        assert result is not None
        assert result["name"] == "success"
        assert result["satisfiable"] is True
        assert "manifest" in result["files"]
        assert "expected_sbom" in result["files"]

    def test_process_fixture_with_lockfile(self, tmp_path: Path):
        case_file = tmp_path / "with-lock.js"
        case_file.write_text("")
        mock_logger = Mock()
        mock_bom_bench = Mock()
        mock_bom_bench.generate_sbom_file = Mock()
        cache_dir = tmp_path / "cache"

        parsed = {
            "name": "with-lock",
            "package_json": {"name": "test"},
            "package_lock": {"lockfileVersion": 3},
        }
        packages = [ResolvedPackage("express", "4.18.2", "https://registry.npmjs.org/express")]

        with patch("bom_bench.fixtures.npm.parse_reify_case", return_value=parsed):
            result = _process_fixture(
                case_file,
                {"with-lock": "lock test"},
                {"lock test": packages},
                mock_bom_bench,
                mock_logger,
                cache_dir,
            )

        assert result is not None
        assert "lock_file" in result["files"]

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
