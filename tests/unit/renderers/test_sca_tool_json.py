"""Tests for SCA tool JSON renderer."""

import json

from bom_bench.renderers.sca_tool_json import register_sca_tool_result_renderer


class TestSCAToolJSONRenderer:
    """Tests for SCA tool JSON renderer."""

    def test_returns_dict_with_filename_and_content(self):
        """Test that renderer returns dict with filename and content keys."""
        summaries = [{"fixture_set": "packse", "tool_name": "cdxgen", "total_scenarios": 5}]

        result = register_sca_tool_result_renderer(tool_name="cdxgen", summaries=summaries)

        assert isinstance(result, dict)
        assert "filename" in result
        assert "content" in result

    def test_filename_is_results_json(self):
        """Test that filename is results.json."""
        summaries = []
        result = register_sca_tool_result_renderer(tool_name="cdxgen", summaries=summaries)

        assert result["filename"] == "results.json"

    def test_content_is_valid_json(self):
        """Test that content is valid JSON."""
        summaries = [
            {
                "fixture_set": "packse",
                "tool_name": "cdxgen",
                "total_scenarios": 10,
                "successful": 8,
                "results": [],
            }
        ]

        result = register_sca_tool_result_renderer(tool_name="cdxgen", summaries=summaries)

        parsed = json.loads(result["content"])
        assert isinstance(parsed, dict)

    def test_includes_tool_name(self):
        """Test that output includes tool name."""
        summaries = [{"fixture_set": "packse", "tool_name": "cdxgen"}]

        result = register_sca_tool_result_renderer(tool_name="cdxgen", summaries=summaries)

        parsed = json.loads(result["content"])
        assert parsed["tool"] == "cdxgen"

    def test_includes_all_fixture_sets(self):
        """Test that output includes all fixture sets."""
        summaries = [
            {"fixture_set": "packse", "tool_name": "cdxgen", "total_scenarios": 5},
            {"fixture_set": "packse2", "tool_name": "cdxgen", "total_scenarios": 3},
        ]

        result = register_sca_tool_result_renderer(tool_name="cdxgen", summaries=summaries)

        parsed = json.loads(result["content"])
        assert "fixture_sets" in parsed
        assert len(parsed["fixture_sets"]) == 2
        assert parsed["fixture_sets"][0]["fixture_set"] == "packse"
        assert parsed["fixture_sets"][1]["fixture_set"] == "packse2"

    def test_content_is_pretty_printed(self):
        """Test that JSON is pretty-printed with indentation."""
        summaries = [{"fixture_set": "packse", "tool_name": "cdxgen"}]

        result = register_sca_tool_result_renderer(tool_name="cdxgen", summaries=summaries)

        assert "\n" in result["content"]
        assert "  " in result["content"]

    def test_includes_results_for_inspection(self):
        """Test that individual results are included for package inspection."""
        summaries = [
            {
                "fixture_set": "packse",
                "tool_name": "cdxgen",
                "results": [
                    {
                        "scenario_name": "test1",
                        "metrics": {
                            "expected_purls": ["pkg:pypi/foo@1.0.0"],
                            "actual_purls": ["pkg:pypi/foo@1.0.0", "pkg:pypi/bar@2.0.0"],
                        },
                    }
                ],
            }
        ]

        result = register_sca_tool_result_renderer(tool_name="cdxgen", summaries=summaries)

        parsed = json.loads(result["content"])
        assert len(parsed["fixture_sets"][0]["results"]) == 1
        assert parsed["fixture_sets"][0]["results"][0]["scenario_name"] == "test1"
        assert "expected_purls" in parsed["fixture_sets"][0]["results"][0]["metrics"]
        assert "actual_purls" in parsed["fixture_sets"][0]["results"][0]["metrics"]
