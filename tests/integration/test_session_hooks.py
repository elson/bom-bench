"""Integration tests for SessionStart hook script."""

import subprocess
from pathlib import Path

import pytest


class TestSessionStartHook:
    """Tests for the install_deps.sh SessionStart hook script."""

    def test_script_exists_and_is_executable(self):
        """Verify the install_deps.sh script exists and has execute permissions."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "install_deps.sh"
        assert script_path.exists(), f"Script not found at {script_path}"
        assert script_path.stat().st_mode & 0o111, "Script should be executable"

    def test_script_exits_early_when_not_remote(self):
        """Script should exit with code 0 when CLAUDE_CODE_REMOTE is not true."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "install_deps.sh"
        result = subprocess.run(
            [str(script_path)],
            env={"CLAUDE_CODE_REMOTE": "false"},
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "Should exit successfully when not remote"
        assert result.stdout == "", "Should produce no output when not remote"

    def test_script_exits_early_when_mise_already_installed(self):
        """Script should exit early if mise is already installed."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "install_deps.sh"

        # Check if mise exists in the current environment
        mise_check = subprocess.run(
            ["which", "mise"],
            capture_output=True,
        )

        if mise_check.returncode != 0:
            pytest.skip("mise not installed in test environment - cannot test early exit")

        # Run with mise in PATH
        result = subprocess.run(
            [str(script_path)],
            env={"CLAUDE_CODE_REMOTE": "true", "PATH": "/usr/local/bin:/usr/bin:/bin"},
            capture_output=True,
            text=True,
        )

        # mise is installed, script should exit early with success
        assert result.returncode == 0
        assert "already installed" in result.stdout

    @pytest.mark.skipif(
        subprocess.run(["which", "npm"], capture_output=True).returncode != 0,
        reason="npm not available in test environment",
    )
    def test_script_attempts_npm_installation(self, tmp_path):
        """Script should attempt npm installation when mise is not found."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "install_deps.sh"

        # Create a minimal environment without mise
        env = {
            "CLAUDE_CODE_REMOTE": "true",
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
        }

        # Remove mise from PATH if it exists
        result = subprocess.run(
            [str(script_path)],
            env=env,
            capture_output=True,
            text=True,
        )

        # The script should either:
        # 1. Successfully install mise via npm (exit 0)
        # 2. Fail to install because npm is not in minimal PATH (exit 1)
        # Both are acceptable outcomes - we're testing the logic flow
        assert result.returncode in [0, 1]

        if result.returncode == 1:
            assert "npm not found" in result.stdout or "npm installation failed" in result.stdout

    def test_script_fails_when_npm_missing(self, tmp_path):
        """Script should fail gracefully when npm is not available."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "install_deps.sh"

        # Create environment without npm
        env = {
            "CLAUDE_CODE_REMOTE": "true",
            "PATH": str(tmp_path),  # Empty PATH with no commands
            "HOME": str(tmp_path),
        }

        result = subprocess.run(
            [str(script_path)],
            env=env,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1, "Should fail when npm is not available"
        assert "npm not found" in result.stdout, "Should report npm not found"
