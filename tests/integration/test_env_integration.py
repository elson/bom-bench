"""Integration tests for environment variable handling."""

from bom_bench.utils import expandvars_dict


class TestEnvIntegration:
    """Integration tests for .env file loading and variable expansion."""

    def test_sca_tool_env_expansion(self, monkeypatch):
        """Test that SCA tool env vars are expanded at registration time."""
        monkeypatch.setenv("MY_API_KEY", "secret123")

        import bom_bench.sca_tools as sca_tools
        from bom_bench.plugins import pm, reset_plugins

        sca_tools._reset_tools()
        reset_plugins()

        # Create a mock plugin that returns a tool with env var
        class MockPlugin:
            def register_sca_tools(self):
                return {
                    "name": "test-tool",
                    "tools": [],
                    "command": "test",
                    "args": ["--key", "${OUTPUT_PATH}"],
                    "env": {"API_KEY": "$MY_API_KEY"},
                }

        # Register the mock plugin with the real pluggy manager
        from bom_bench import hookimpl

        # Add hookimpl decorator to the method
        MockPlugin.register_sca_tools = hookimpl(MockPlugin.register_sca_tools)

        mock_plugin = MockPlugin()
        pm.register(mock_plugin, name="test_mock_env_plugin")

        # Re-register tools with the updated plugin manager
        sca_tools._register_tools(pm)

        # Verify env was expanded but args were not
        tool_data = sca_tools._registered_tool_data["test-tool"]
        assert tool_data["env"]["API_KEY"] == "secret123"
        assert tool_data["args"] == ["--key", "${OUTPUT_PATH}"]

        # Cleanup
        pm.unregister(mock_plugin)

    def test_fixture_env_expansion(self, monkeypatch, tmp_path):
        """Test that fixture set env vars are expanded at load time."""
        monkeypatch.setenv("MY_INDEX_URL", "http://localhost:3141")

        from bom_bench.fixtures.loader import FixtureSetLoader

        # Create fixture files
        fixture_dir = tmp_path / "fixture1"
        fixture_dir.mkdir()
        (fixture_dir / "pyproject.toml").write_text('[project]\nname = "test"')
        (fixture_dir / "meta.json").write_text('{"satisfiable": true}')

        # Create a mock plugin manager
        class MockHook:
            def register_fixture_sets(self, bom_bench):
                return [
                    [
                        {
                            "name": "test-set",
                            "description": "Test",
                            "ecosystem": "python",
                            "environment": {
                                "tools": [],
                                "env": {"INDEX_URL": "$MY_INDEX_URL"},
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
                                }
                            ],
                        }
                    ]
                ]

        class MockPM:
            hook = MockHook()

        loader = FixtureSetLoader(pm=MockPM())
        fixture_sets = loader.load_all()

        assert len(fixture_sets) == 1
        assert fixture_sets[0].environment.env["INDEX_URL"] == "http://localhost:3141"

    def test_format_command_expands_runtime_vars(self):
        """Test that format_command expands output_path and project_dir at runtime."""
        from bom_bench.models.sca_tool import SCAToolConfig

        config = SCAToolConfig(
            name="test",
            tools=[],
            command="scan",
            args=["--output", "${OUTPUT_PATH}", "${PROJECT_DIR}"],
        )

        result = config.format_command(
            output_path="/tmp/out.json",
            project_dir="/my/project",
        )

        assert result == "scan --output /tmp/out.json /my/project"

    def test_env_var_with_default(self, monkeypatch):
        """Test that default values work when var is not set."""
        monkeypatch.delenv("MISSING_VAR", raising=False)

        result = expandvars_dict({"key": "${MISSING_VAR:-default_value}"})

        assert result["key"] == "default_value"

    def test_env_var_default_not_used_when_set(self, monkeypatch):
        """Test that default is not used when var is set."""
        monkeypatch.setenv("EXISTS", "actual_value")

        result = expandvars_dict({"key": "${EXISTS:-default}"})

        assert result["key"] == "actual_value"
