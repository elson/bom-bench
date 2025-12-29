"""Tests for Syft plugin."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from bom_bench.sca_tools.syft import (
    _get_syft_version,
    register_sca_tools,
    scan_project,
)


class TestSyftVersionDetection:
    """Tests for Syft version detection."""

    @patch("subprocess.run")
    def test_get_syft_version_success(self, mock_run):
        """Test successful version extraction."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Application:   syft\nVersion:       1.39.0\nBuildDate:     2025-12-22T19:51:39Z\n"
        )

        version = _get_syft_version()

        assert version == "1.39.0"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_get_syft_version_not_installed(self, mock_run):
        """Test when Syft is not installed."""
        mock_run.side_effect = FileNotFoundError()

        version = _get_syft_version()

        assert version is None

    @patch("subprocess.run")
    def test_get_syft_version_timeout(self, mock_run):
        """Test version command timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("syft", 10)

        version = _get_syft_version()

        assert version is None

    @patch("subprocess.run")
    def test_get_syft_version_non_zero_exit(self, mock_run):
        """Test non-zero exit code."""
        mock_run.return_value = MagicMock(returncode=1)

        version = _get_syft_version()

        assert version is None

    @patch("subprocess.run")
    def test_get_syft_version_no_version_line(self, mock_run):
        """Test when output doesn't contain Version: line."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Application:   syft\nBuildDate:     2025-12-22T19:51:39Z\n"
        )

        version = _get_syft_version()

        assert version is None


class TestSyftToolRegistration:
    """Tests for Syft tool registration."""

    def test_syft_registers_correctly(self):
        """Test that Syft registers with correct info."""
        tool = register_sca_tools()

        assert tool["name"] == "syft"
        assert tool["homepage"] == "https://github.com/anchore/syft"

    def test_syft_supported_ecosystems(self):
        """Test Syft supported ecosystems."""
        tool = register_sca_tools()

        ecosystems = tool["supported_ecosystems"]
        assert "python" in ecosystems
        assert "javascript" in ecosystems
        assert "java" in ecosystems
        assert "go" in ecosystems
        assert "rust" in ecosystems
        assert "ruby" in ecosystems
        assert "php" in ecosystems
        assert "dotnet" in ecosystems

    @patch("bom_bench.sca_tools.syft._get_syft_version")
    def test_syft_tool_info_has_version(self, mock_version):
        """Test that tool info includes version."""
        mock_version.return_value = "1.39.0"

        tool = register_sca_tools()

        assert tool["version"] == "1.39.0"


class TestSyftAvailabilityCheck:
    """Tests for Syft availability check via installed field."""

    @patch("shutil.which")
    def test_syft_installed_when_available(self, mock_which):
        """Test installed field when Syft is installed."""
        mock_which.return_value = "/usr/local/bin/syft"

        tool = register_sca_tools()

        assert tool["installed"] is True
        mock_which.assert_called_with("syft")

    @patch("shutil.which")
    def test_syft_not_installed_when_missing(self, mock_which):
        """Test installed field when Syft is not installed."""
        mock_which.return_value = None

        tool = register_sca_tools()

        assert tool["installed"] is False


class TestSyftSBOMGeneration:
    """Tests for Syft SBOM generation."""

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open, read_data='{"bomFormat": "CycloneDX"}')
    @patch("pathlib.Path.exists")
    def test_generate_sbom_success(self, mock_exists, mock_file, mock_run, tmp_path):
        """Test successful SBOM generation."""
        project_dir = tmp_path / "project"
        output_path = tmp_path / "output.json"

        mock_run.return_value = MagicMock(returncode=0, stderr="")
        mock_exists.return_value = True

        result = scan_project(
            tool_name="syft",
            project_dir=project_dir,
            output_path=output_path,
            ecosystem="python"
        )

        assert result is not None
        assert result["tool_name"] == "syft"
        assert result["status"] == "success"
        assert result["sbom_path"] == str(output_path)
        assert result["duration_seconds"] > 0

        # Verify command was called correctly
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "syft"
        assert str(project_dir) in cmd
        assert f"cyclonedx-json={output_path}" in cmd

    @patch("subprocess.run")
    def test_generate_sbom_timeout(self, mock_run, tmp_path):
        """Test SBOM generation timeout."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("syft", 120)

        result = scan_project(
            tool_name="syft",
            project_dir=tmp_path,
            output_path=tmp_path / "out.json",
            ecosystem="python"
        )

        assert result is not None
        assert result["status"] == "timeout"
        assert "Timeout" in result["error_message"]

    @patch("subprocess.run")
    def test_generate_sbom_tool_not_found(self, mock_run, tmp_path):
        """Test when Syft is not found."""
        mock_run.side_effect = FileNotFoundError()

        result = scan_project(
            tool_name="syft",
            project_dir=tmp_path,
            output_path=tmp_path / "out.json",
            ecosystem="python"
        )

        assert result is not None
        assert result["status"] == "tool_not_found"
        assert "syft not found" in result["error_message"]

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open, read_data='invalid json{')
    @patch("pathlib.Path.exists")
    def test_generate_sbom_invalid_json(self, mock_exists, mock_file, mock_run, tmp_path):
        """Test handling of invalid JSON output."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        mock_exists.return_value = True

        result = scan_project(
            tool_name="syft",
            project_dir=tmp_path,
            output_path=tmp_path / "out.json",
            ecosystem="python"
        )

        assert result is not None
        assert result["status"] == "parse_error"
        assert "Invalid JSON" in result["error_message"]

    @patch("subprocess.run")
    def test_generate_sbom_non_zero_exit(self, mock_run, tmp_path):
        """Test non-zero exit code handling."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Error: could not determine source"
        )

        result = scan_project(
            tool_name="syft",
            project_dir=tmp_path,
            output_path=tmp_path / "out.json",
            ecosystem="python"
        )

        assert result is not None
        assert result["status"] == "tool_failed"
        assert "could not determine source" in result["error_message"]

    def test_generate_sbom_wrong_tool(self, tmp_path):
        """Test that plugin returns None for other tools."""
        result = scan_project(
            tool_name="cdxgen",
            project_dir=tmp_path,
            output_path=tmp_path / "out.json",
            ecosystem="python"
        )

        assert result is None

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=mock_open, read_data='{"bomFormat": "CycloneDX"}')
    @patch("pathlib.Path.exists")
    def test_generate_sbom_creates_output_dir(self, mock_exists, mock_file, mock_run, tmp_path):
        """Test that output directory is created."""
        project_dir = tmp_path / "project"
        output_path = tmp_path / "nested" / "dir" / "output.json"

        mock_run.return_value = MagicMock(returncode=0, stderr="")
        mock_exists.return_value = True

        result = scan_project(
            tool_name="syft",
            project_dir=project_dir,
            output_path=output_path,
            ecosystem="python"
        )

        # The parent directory should have been created
        assert output_path.parent.exists()

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_generate_sbom_no_output_file(self, mock_exists, mock_run, tmp_path):
        """Test when command succeeds but no file is created."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        mock_exists.return_value = False

        result = scan_project(
            tool_name="syft",
            project_dir=tmp_path,
            output_path=tmp_path / "out.json",
            ecosystem="python"
        )

        assert result is not None
        assert result["status"] == "tool_failed"
