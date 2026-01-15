"""Test runner for npm arborist tests with fixture preservation."""

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestRunResult:
    """Result of running arborist tests."""

    success: bool
    fixtures_dir: Path
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float


def run_arborist_tests(npm_cli_dir: Path, timeout: int = 600) -> TestRunResult:
    """Run arborist reify tests with --save-fixture flag.

    Args:
        npm_cli_dir: Path to npm/cli repository
        timeout: Timeout in seconds (default 10 minutes)

    Returns:
        TestRunResult with execution details and path to saved fixtures
    """
    arborist_dir = npm_cli_dir / "workspaces" / "arborist"
    test_dir = arborist_dir / "test" / "arborist"

    start_time = time.time()

    # First, install dependencies with npm ci
    try:
        subprocess.run(
            ["npm", "ci"],
            cwd=arborist_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        return TestRunResult(
            success=False,
            fixtures_dir=test_dir,
            exit_code=e.returncode,
            stdout=e.stdout,
            stderr=e.stderr,
            duration_seconds=duration,
        )
    except subprocess.TimeoutExpired as e:
        duration = time.time() - start_time
        return TestRunResult(
            success=False,
            fixtures_dir=test_dir,
            exit_code=-1,
            stdout=e.stdout.decode() if e.stdout else "",
            stderr=e.stderr.decode() if e.stderr else "",
            duration_seconds=duration,
        )

    # Run tests with --save-fixture flag
    try:
        result = subprocess.run(
            ["npx", "tap", "test/arborist/reify.js", "--save-fixture", "--no-coverage"],
            cwd=arborist_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = time.time() - start_time

        # Tests may have some failures but still produce fixtures
        # Consider success if exit code is 0 or 1 (some tests failed but ran)
        success = result.returncode in (0, 1)

        return TestRunResult(
            success=success,
            fixtures_dir=test_dir,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_seconds=duration,
        )
    except subprocess.TimeoutExpired as e:
        duration = time.time() - start_time
        return TestRunResult(
            success=False,
            fixtures_dir=test_dir,
            exit_code=-1,
            stdout=e.stdout.decode() if e.stdout else "",
            stderr=e.stderr.decode() if e.stderr else "",
            duration_seconds=duration,
        )
