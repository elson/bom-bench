"""Tests for npm fixture mapper."""

from pathlib import Path


class TestNameConversion:
    """Tests for name conversion functions."""

    def test_directory_to_test_name_simple(self):
        """Test converting simple directory name to test name."""
        from bom_bench.fixtures.npm.fixture_mapper import directory_to_test_name

        assert (
            directory_to_test_name("tap-testdir-reify-link-meta-deps-update")
            == "link meta deps update"
        )

    def test_directory_to_test_name_complex(self):
        """Test converting complex directory name."""
        from bom_bench.fixtures.npm.fixture_mapper import directory_to_test_name

        assert (
            directory_to_test_name(
                "tap-testdir-reify-add-a-dep-present-in-the-tree-with-v1-shrinkwrap"
            )
            == "add a dep present in the tree with v1 shrinkwrap"
        )

    def test_test_name_to_directory_simple(self):
        """Test converting test name to directory name."""
        from bom_bench.fixtures.npm.fixture_mapper import test_name_to_directory

        assert (
            test_name_to_directory("link meta deps, update")
            == "tap-testdir-reify-link-meta-deps-update"
        )

    def test_test_name_to_directory_removes_commas(self):
        """Test that commas are removed from test names."""
        from bom_bench.fixtures.npm.fixture_mapper import test_name_to_directory

        assert (
            test_name_to_directory("link meta deps, fresh install")
            == "tap-testdir-reify-link-meta-deps-fresh-install"
        )

    def test_sanitize_test_name_removes_commas_and_spaces(self):
        """Test sanitize_test_name function."""
        from bom_bench.fixtures.npm.fixture_mapper import sanitize_test_name

        assert sanitize_test_name("link meta deps, update") == "link-meta-deps-update"

    def test_sanitize_test_name_handles_multiple_commas(self):
        """Test sanitizing name with multiple commas."""
        from bom_bench.fixtures.npm.fixture_mapper import sanitize_test_name

        assert sanitize_test_name("test, case, name") == "test-case-name"


class TestFixtureMappingEntry:
    """Tests for FixtureMappingEntry dataclass."""

    def test_fixture_mapping_entry_creation(self, tmp_path: Path):
        """Test creating FixtureMappingEntry."""
        from bom_bench.fixtures.npm.fixture_mapper import FixtureMappingEntry

        entry = FixtureMappingEntry(
            fixture_name="link-meta-deps-update",
            test_name="link meta deps, update",
            saved_dir=tmp_path / "saved",
            snapshot_prefix="test/arborist/reify.js TAP link meta deps, update",
        )

        assert entry.fixture_name == "link-meta-deps-update"
        assert entry.test_name == "link meta deps, update"
        assert entry.saved_dir == tmp_path / "saved"
        assert entry.snapshot_prefix == "test/arborist/reify.js TAP link meta deps, update"


class TestBuildFixtureMapping:
    """Tests for build_fixture_mapping function."""

    def test_build_fixture_mapping_from_directories(self, tmp_path: Path):
        """Test building mapping from saved directories."""
        from bom_bench.fixtures.npm.fixture_mapper import build_fixture_mapping

        # Create mock directory structure
        fixtures_dir = tmp_path / "test" / "arborist"
        (fixtures_dir / "tap-testdir-reify-link-meta-deps-update").mkdir(parents=True)
        (fixtures_dir / "tap-testdir-reify-link-deps-already-in-place").mkdir(parents=True)

        # Create mock snapshot file
        snapshot_file = tmp_path / "reify.js.test.cjs"
        snapshot_content = """
exports[`test/arborist/reify.js TAP link meta deps, update > expect resolving Promise 1`] = `foo`;
exports[`test/arborist/reify.js TAP link deps already in place > expect resolving Promise 1`] = `bar`;
"""
        snapshot_file.write_text(snapshot_content)

        mapping = build_fixture_mapping(snapshot_file, fixtures_dir)

        assert "link-meta-deps-update" in mapping
        assert mapping["link-meta-deps-update"].fixture_name == "link-meta-deps-update"
        assert mapping["link-meta-deps-update"].test_name == "link meta deps, update"
        assert (
            mapping["link-meta-deps-update"].saved_dir
            == fixtures_dir / "tap-testdir-reify-link-meta-deps-update"
        )
        assert (
            mapping["link-meta-deps-update"].snapshot_prefix
            == "test/arborist/reify.js TAP link meta deps, update"
        )

    def test_build_fixture_mapping_skips_non_matching(self, tmp_path: Path):
        """Test that non-matching directories are skipped."""
        from bom_bench.fixtures.npm.fixture_mapper import build_fixture_mapping

        fixtures_dir = tmp_path / "test" / "arborist"
        (fixtures_dir / "tap-testdir-reify-valid-test").mkdir(parents=True)
        (fixtures_dir / "other-directory").mkdir(parents=True)  # Should be ignored

        snapshot_file = tmp_path / "reify.js.test.cjs"
        snapshot_content = """
exports[`test/arborist/reify.js TAP valid test > expect resolving Promise 1`] = `foo`;
"""
        snapshot_file.write_text(snapshot_content)

        mapping = build_fixture_mapping(snapshot_file, fixtures_dir)

        assert "valid-test" in mapping
        assert "other-directory" not in mapping
        assert len(mapping) == 1

    def test_build_fixture_mapping_handles_complex_names(self, tmp_path: Path):
        """Test mapping with complex test names."""
        from bom_bench.fixtures.npm.fixture_mapper import build_fixture_mapping

        fixtures_dir = tmp_path / "test" / "arborist"
        dir_name = "tap-testdir-reify-add-a-dep-present-in-the-tree-with-v1-shrinkwrap"
        (fixtures_dir / dir_name).mkdir(parents=True)

        snapshot_file = tmp_path / "reify.js.test.cjs"
        snapshot_content = """
exports[`test/arborist/reify.js TAP add a dep present in the tree, with v1 shrinkwrap > must match snapshot 1`] = `foo`;
"""
        snapshot_file.write_text(snapshot_content)

        mapping = build_fixture_mapping(snapshot_file, fixtures_dir)

        key = "add-a-dep-present-in-the-tree-with-v1-shrinkwrap"
        assert key in mapping
        assert mapping[key].saved_dir.name == dir_name

    def test_build_fixture_mapping_empty_snapshot(self, tmp_path: Path):
        """Test with empty snapshot file."""
        from bom_bench.fixtures.npm.fixture_mapper import build_fixture_mapping

        fixtures_dir = tmp_path / "test" / "arborist"
        (fixtures_dir / "tap-testdir-reify-test").mkdir(parents=True)

        snapshot_file = tmp_path / "reify.js.test.cjs"
        snapshot_file.write_text("")

        mapping = build_fixture_mapping(snapshot_file, fixtures_dir)

        # Should still find directory but might not match to snapshot
        # Implementation can decide how to handle this
        assert isinstance(mapping, dict)

    def test_build_fixture_mapping_no_directories(self, tmp_path: Path):
        """Test with no fixture directories."""
        from bom_bench.fixtures.npm.fixture_mapper import build_fixture_mapping

        fixtures_dir = tmp_path / "test" / "arborist"
        fixtures_dir.mkdir(parents=True)

        snapshot_file = tmp_path / "reify.js.test.cjs"
        snapshot_file.write_text("exports[`test/arborist/reify.js TAP test > foo 1`] = `bar`;")

        mapping = build_fixture_mapping(snapshot_file, fixtures_dir)

        assert mapping == {}
