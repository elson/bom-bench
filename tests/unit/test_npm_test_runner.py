"""Tests for npm test runner."""

from pathlib import Path
from unittest.mock import Mock, patch


class TestTestRunner:
    """Tests for arborist test runner."""

    def test_run_arborist_tests_success(self, tmp_path: Path):
        """Test successful execution of arborist tests."""
        from bom_bench.fixtures.npm.test_runner import run_arborist_tests

        npm_cli_dir = tmp_path / "npm-cli"
        arborist_dir = npm_cli_dir / "workspaces" / "arborist"
        test_dir = arborist_dir / "test" / "arborist"
        test_dir.mkdir(parents=True, exist_ok=True)

        with patch("subprocess.run") as mock_run:
            # Mock successful npm ci
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            # On second call (tap test), return success
            def side_effect(*args, **_kwargs):
                if "npm" in args[0]:
                    return Mock(returncode=0, stdout="npm ci success", stderr="")
                else:  # tap test
                    return Mock(returncode=0, stdout="tests passed", stderr="")

            mock_run.side_effect = side_effect

            result = run_arborist_tests(npm_cli_dir, timeout=60)

            assert result.success is True
            assert result.exit_code == 0
            assert result.fixtures_dir == test_dir
            assert result.duration_seconds >= 0
            assert "tests passed" in result.stdout

    def test_run_arborist_tests_npm_ci_failure(self, tmp_path: Path):
        """Test failure during npm ci."""
        from bom_bench.fixtures.npm.test_runner import run_arborist_tests

        npm_cli_dir = tmp_path / "npm-cli"
        arborist_dir = npm_cli_dir / "workspaces" / "arborist"
        test_dir = arborist_dir / "test" / "arborist"
        test_dir.mkdir(parents=True, exist_ok=True)

        with patch("subprocess.run") as mock_run:
            from subprocess import CalledProcessError

            mock_run.side_effect = CalledProcessError(
                returncode=1, cmd=["npm", "ci"], output="install failed", stderr="error"
            )

            result = run_arborist_tests(npm_cli_dir, timeout=60)

            assert result.success is False
            assert result.exit_code == 1
            assert result.fixtures_dir == test_dir

    def test_run_arborist_tests_with_some_test_failures(self, tmp_path: Path):
        """Test when some tests fail but fixtures are still generated."""
        from bom_bench.fixtures.npm.test_runner import run_arborist_tests

        npm_cli_dir = tmp_path / "npm-cli"
        arborist_dir = npm_cli_dir / "workspaces" / "arborist"
        test_dir = arborist_dir / "test" / "arborist"
        test_dir.mkdir(parents=True, exist_ok=True)

        with patch("subprocess.run") as mock_run:

            def side_effect(*args, **_kwargs):
                if "npm" in args[0]:
                    return Mock(returncode=0, stdout="", stderr="")
                else:  # tap test - exit 1 means some tests failed
                    return Mock(returncode=1, stdout="some tests failed", stderr="")

            mock_run.side_effect = side_effect

            result = run_arborist_tests(npm_cli_dir, timeout=60)

            # Exit code 1 is acceptable (some tests failed but fixtures created)
            assert result.success is True
            assert result.exit_code == 1
            assert result.fixtures_dir == test_dir

    def test_run_arborist_tests_timeout(self, tmp_path: Path):
        """Test timeout handling."""
        from bom_bench.fixtures.npm.test_runner import run_arborist_tests

        npm_cli_dir = tmp_path / "npm-cli"
        arborist_dir = npm_cli_dir / "workspaces" / "arborist"
        test_dir = arborist_dir / "test" / "arborist"
        test_dir.mkdir(parents=True, exist_ok=True)

        with patch("subprocess.run") as mock_run:
            from subprocess import TimeoutExpired

            def side_effect(*args, **_kwargs):
                if "npm" in args[0]:
                    return Mock(returncode=0, stdout="", stderr="")
                else:
                    raise TimeoutExpired(
                        cmd=args[0], timeout=60, output=b"partial output", stderr=b"timeout"
                    )

            mock_run.side_effect = side_effect

            result = run_arborist_tests(npm_cli_dir, timeout=60)

            assert result.success is False
            assert result.exit_code == -1
            assert "partial output" in result.stdout
            assert "timeout" in result.stderr

    def test_run_arborist_tests_npm_ci_timeout(self, tmp_path: Path):
        """Test timeout during npm ci."""
        from bom_bench.fixtures.npm.test_runner import run_arborist_tests

        npm_cli_dir = tmp_path / "npm-cli"
        arborist_dir = npm_cli_dir / "workspaces" / "arborist"
        test_dir = arborist_dir / "test" / "arborist"
        test_dir.mkdir(parents=True, exist_ok=True)

        with patch("subprocess.run") as mock_run:
            from subprocess import TimeoutExpired

            mock_run.side_effect = TimeoutExpired(
                cmd=["npm", "ci"], timeout=60, output=b"installing", stderr=b"timeout"
            )

            result = run_arborist_tests(npm_cli_dir, timeout=60)

            assert result.success is False
            assert result.exit_code == -1


class TestTestRunResult:
    """Tests for TestRunResult dataclass."""

    def test_test_run_result_creation(self, tmp_path: Path):
        """Test creating TestRunResult."""
        from bom_bench.fixtures.npm.test_runner import TestRunResult

        result = TestRunResult(
            success=True,
            fixtures_dir=tmp_path,
            exit_code=0,
            stdout="output",
            stderr="",
            duration_seconds=1.5,
        )

        assert result.success is True
        assert result.fixtures_dir == tmp_path
        assert result.exit_code == 0
        assert result.stdout == "output"
        assert result.stderr == ""
        assert result.duration_seconds == 1.5
