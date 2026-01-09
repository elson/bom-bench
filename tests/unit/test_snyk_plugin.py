"""Tests for Snyk plugin."""

import json

import pytest

from bom_bench.sca_tools.snyk import (
    _extract_dependencies,
    _parse_snyk_output,
    handle_sca_tool_response,
    register_sca_tools,
)


class TestSnykToolRegistration:
    """Tests for Snyk tool registration."""

    def test_snyk_registers_correctly(self):
        """Test that Snyk registers with correct info."""
        tool = register_sca_tools()

        assert tool["name"] == "snyk"
        assert tool["description"] == "Snyk CLI - security testing and dependency analysis"
        assert tool["homepage"] == "https://docs.snyk.io/"

    def test_snyk_supported_ecosystems(self):
        """Test Snyk supported ecosystems."""
        tool = register_sca_tools()

        ecosystems = tool["supported_ecosystems"]
        assert "python" in ecosystems
        assert "javascript" in ecosystems
        assert "java" in ecosystems
        assert "go" in ecosystems
        assert "ruby" in ecosystems
        assert "php" in ecosystems
        assert "dotnet" in ecosystems

    def test_snyk_has_declarative_config(self):
        """Test that tool has declarative config for sandbox execution."""
        tool = register_sca_tools()

        assert "tools" in tool
        assert tool["tools"] == [{"name": "npm:snyk", "version": "1.1301.2"}]
        assert "command" in tool
        assert tool["command"] == "snyk"
        assert "args" in tool
        assert "${PROJECT_DIR}" in tool["args"]
        assert any("${OUTPUT_PATH}" in arg for arg in tool["args"])

    def test_snyk_uses_shell_redirection(self):
        """Test that Snyk command uses shell redirection."""
        tool = register_sca_tools()

        args = tool["args"]
        assert ">" in args
        assert "||" in args or "|" in args

    def test_snyk_requires_api_token(self):
        """Test that Snyk requires SNYK_TOKEN env var."""
        tool = register_sca_tools()

        assert "env" in tool
        assert "SNYK_TOKEN" in tool["env"]
        assert "${SNYK_TOKEN}" in tool["env"]["SNYK_TOKEN"]


class TestExtractDependencies:
    """Tests for _extract_dependencies function."""

    def test_extract_simple_dependency(self):
        """Test extracting a single dependency."""
        dep_tree = {"name": "package1", "version": "1.0.0"}

        packages = _extract_dependencies(dep_tree)

        assert len(packages) == 1
        assert packages[0] == {"name": "package1", "version": "1.0.0"}

    def test_extract_nested_dependencies(self):
        """Test extracting nested dependencies."""
        dep_tree = {
            "name": "root",
            "version": "1.0.0",
            "dependencies": {
                "dep1": {"name": "dep1", "version": "2.0.0"},
                "dep2": {"name": "dep2", "version": "3.0.0"},
            },
        }

        packages = _extract_dependencies(dep_tree)

        assert len(packages) == 3
        names = [p["name"] for p in packages]
        assert "root" in names
        assert "dep1" in names
        assert "dep2" in names

    def test_extract_deeply_nested_dependencies(self):
        """Test extracting arbitrarily deeply nested dependencies."""
        dep_tree = {
            "name": "root",
            "version": "1.0.0",
            "dependencies": {
                "dep1": {
                    "name": "dep1",
                    "version": "2.0.0",
                    "dependencies": {
                        "dep2": {
                            "name": "dep2",
                            "version": "3.0.0",
                            "dependencies": {"dep3": {"name": "dep3", "version": "4.0.0"}},
                        }
                    },
                }
            },
        }

        packages = _extract_dependencies(dep_tree)

        assert len(packages) == 4
        names = [p["name"] for p in packages]
        assert "root" in names
        assert "dep1" in names
        assert "dep2" in names
        assert "dep3" in names

    def test_extract_with_labels(self):
        """Test extracting dependencies that have labels field."""
        dep_tree = {
            "name": "@dansmaculotte/nuxt-segment",
            "version": "0.2.5",
            "labels": {"scope": "prod"},
            "dependencies": {
                "@dansmaculotte/vue-segment": {
                    "name": "@dansmaculotte/vue-segment",
                    "version": "0.2.6",
                    "labels": {"scope": "prod"},
                }
            },
        }

        packages = _extract_dependencies(dep_tree)

        assert len(packages) == 2
        assert packages[0]["name"] == "@dansmaculotte/nuxt-segment"
        assert packages[1]["name"] == "@dansmaculotte/vue-segment"

    def test_extract_empty_dependencies(self):
        """Test extracting from tree with no dependencies."""
        dep_tree = {"name": "standalone", "version": "1.0.0", "dependencies": {}}

        packages = _extract_dependencies(dep_tree)

        assert len(packages) == 1
        assert packages[0] == {"name": "standalone", "version": "1.0.0"}

    def test_extract_missing_dependencies_field(self):
        """Test extracting when dependencies field is missing."""
        dep_tree = {"name": "simple", "version": "1.0.0"}

        packages = _extract_dependencies(dep_tree)

        assert len(packages) == 1
        assert packages[0] == {"name": "simple", "version": "1.0.0"}

    def test_extract_whitespace_only_values(self):
        """Test extracting filters out whitespace-only name/version."""
        dep_tree = {
            "name": "  ",
            "version": "  ",
            "dependencies": {
                "valid": {"name": "valid-pkg", "version": "1.0.0"},
                "whitespace": {"name": " \t ", "version": " \n "},
            },
        }

        packages = _extract_dependencies(dep_tree)

        assert len(packages) == 1
        assert packages[0]["name"] == "valid-pkg"

    def test_extract_strips_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        dep_tree = {"name": "  package  ", "version": "  1.0.0  "}

        packages = _extract_dependencies(dep_tree)

        assert len(packages) == 1
        assert packages[0] == {"name": "package", "version": "1.0.0"}


class TestParseSnykOutput:
    """Tests for _parse_snyk_output function."""

    def test_parse_valid_concatenated_json(self):
        """Test parsing valid concatenated JSON output."""
        output = """{"name": "agilemetrics", "version": "1.0.1", "dependencies": {"package1": {"name": "package1", "version": "2.0.0"}}}{"vulnerabilities": []}"""

        packages = _parse_snyk_output(output)

        assert len(packages) == 2
        names = [p["name"] for p in packages]
        assert "agilemetrics" in names
        assert "package1" in names

    def test_parse_error_response(self):
        """Test parsing error response with ok: false."""
        output = """{
            "ok": false,
            "error": "Could not detect supported target files",
            "path": "assets/"
        }"""

        packages = _parse_snyk_output(output)

        assert packages == []

    def test_parse_complex_nested_structure(self):
        """Test parsing complex nested dependency structure from issue example."""
        output = """{
            "name": "agilemetrics",
            "version": "1.0.1",
            "dependencies": {
                "@dansmaculotte/nuxt-segment": {
                    "name": "@dansmaculotte/nuxt-segment",
                    "version": "0.2.5",
                    "labels": {"scope": "prod"},
                    "dependencies": {
                        "@dansmaculotte/vue-segment": {
                            "name": "@dansmaculotte/vue-segment",
                            "version": "0.2.6",
                            "labels": {"scope": "prod"}
                        }
                    }
                }
            }
        }{"vulnerabilities": [{"id": "SNYK-123"}]}"""

        packages = _parse_snyk_output(output)

        assert len(packages) == 3
        names = [p["name"] for p in packages]
        assert "agilemetrics" in names
        assert "@dansmaculotte/nuxt-segment" in names
        assert "@dansmaculotte/vue-segment" in names

    def test_parse_removes_duplicates(self):
        """Test that duplicate packages are removed."""
        output = """{
            "name": "root",
            "version": "1.0.0",
            "dependencies": {
                "shared": {"name": "shared", "version": "2.0.0"},
                "dep1": {
                    "name": "dep1",
                    "version": "1.0.0",
                    "dependencies": {
                        "shared": {"name": "shared", "version": "2.0.0"}
                    }
                }
            }
        }{"vulnerabilities": []}"""

        packages = _parse_snyk_output(output)

        assert len(packages) == 3
        names = [p["name"] for p in packages]
        assert names.count("shared") == 1

    def test_parse_whitespace_handling(self):
        """Test parsing handles leading/trailing whitespace."""
        output = """  \n  {"name": "pkg", "version": "1.0.0"}{"vulnerabilities": []}  \n  """

        packages = _parse_snyk_output(output)

        assert len(packages) == 1
        assert packages[0]["name"] == "pkg"

    def test_parse_malformed_json(self):
        """Test parsing malformed JSON returns empty list."""
        output = """{"name": "test", "invalid": json}"""

        packages = _parse_snyk_output(output)

        assert packages == []

    def test_parse_incomplete_json(self):
        """Test parsing incomplete JSON returns empty list."""
        output = """{"name": "test", "version": """

        packages = _parse_snyk_output(output)

        assert packages == []

    def test_parse_empty_string(self):
        """Test parsing empty string returns empty list."""
        packages = _parse_snyk_output("")

        assert packages == []

    def test_parse_non_json_text(self):
        """Test parsing non-JSON text returns empty list."""
        output = "Error: Could not find package.json"

        packages = _parse_snyk_output(output)

        assert packages == []


class TestHandleScaToolResponse:
    """Tests for handle_sca_tool_response hook."""

    @pytest.fixture
    def mock_bom_bench(self):
        """Create mock bom_bench module with generate_cyclonedx_sbom function."""

        class MockBomBench:
            @staticmethod
            def generate_cyclonedx_sbom(scenario_name, packages):
                return {
                    "bomFormat": "CycloneDX",
                    "specVersion": "1.6",
                    "metadata": {
                        "component": {
                            "name": scenario_name,
                            "type": "application",
                        }
                    },
                    "components": [
                        {
                            "name": pkg["name"],
                            "version": pkg["version"],
                            "type": "library",
                        }
                        for pkg in packages
                    ],
                }

        return MockBomBench()

    def test_handle_response_with_output_file(self, mock_bom_bench):
        """Test handling response when output is in file."""
        output_contents = """{
            "name": "project",
            "version": "1.0.0",
            "dependencies": {
                "dep1": {"name": "dep1", "version": "2.0.0"}
            }
        }{"vulnerabilities": []}"""

        result = handle_sca_tool_response(
            bom_bench=mock_bom_bench,
            stdout="",
            stderr="",
            output_file_contents=output_contents,
        )

        assert result is not None
        sbom = json.loads(result)
        assert sbom["bomFormat"] == "CycloneDX"
        assert len(sbom["components"]) == 2

    def test_handle_response_with_stdout(self, mock_bom_bench):
        """Test handling response when output is in stdout."""
        stdout = """{
            "name": "project",
            "version": "1.0.0",
            "dependencies": {
                "dep1": {"name": "dep1", "version": "2.0.0"}
            }
        }{"vulnerabilities": []}"""

        result = handle_sca_tool_response(
            bom_bench=mock_bom_bench,
            stdout=stdout,
            stderr="",
            output_file_contents=None,
        )

        assert result is not None
        sbom = json.loads(result)
        assert sbom["bomFormat"] == "CycloneDX"
        assert len(sbom["components"]) == 2

    def test_handle_response_prefers_output_file(self, mock_bom_bench):
        """Test that output_file_contents is preferred over stdout."""
        output_contents = """{"name": "from-file", "version": "1.0.0"}{"vulnerabilities": []}"""
        stdout = """{"name": "from-stdout", "version": "2.0.0"}{"vulnerabilities": []}"""

        result = handle_sca_tool_response(
            bom_bench=mock_bom_bench,
            stdout=stdout,
            stderr="",
            output_file_contents=output_contents,
        )

        assert result is not None
        sbom = json.loads(result)
        names = [c["name"] for c in sbom["components"]]
        assert "from-file" in names
        assert "from-stdout" not in names

    def test_handle_response_with_error(self, mock_bom_bench):
        """Test handling response when Snyk returns error."""
        output_contents = """{
            "ok": false,
            "error": "Could not detect supported target files",
            "path": "assets/"
        }"""

        result = handle_sca_tool_response(
            bom_bench=mock_bom_bench,
            stdout="",
            stderr="",
            output_file_contents=output_contents,
        )

        assert result is None

    def test_handle_response_with_empty_output(self, mock_bom_bench):
        """Test handling response when output is empty."""
        result = handle_sca_tool_response(
            bom_bench=mock_bom_bench,
            stdout="",
            stderr="",
            output_file_contents="",
        )

        assert result is None

    def test_handle_response_with_no_packages(self, mock_bom_bench):
        """Test handling response when no packages are extracted."""
        output_contents = """{"name": "", "version": ""}{"vulnerabilities": []}"""

        result = handle_sca_tool_response(
            bom_bench=mock_bom_bench,
            stdout="",
            stderr="",
            output_file_contents=output_contents,
        )

        assert result is None

    def test_handle_response_generates_valid_json(self, mock_bom_bench):
        """Test that response hook generates valid JSON string."""
        output_contents = """{"name": "test", "version": "1.0.0"}{"vulnerabilities": []}"""

        result = handle_sca_tool_response(
            bom_bench=mock_bom_bench,
            stdout="",
            stderr="",
            output_file_contents=output_contents,
        )

        assert result is not None
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
