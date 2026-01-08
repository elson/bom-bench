from pathlib import Path
from unittest.mock import MagicMock, patch

from bom_bench.sandbox.mise import MiseRunner, ToolSpec, generate_mise_toml


class TestToolSpec:
    def test_create_tool_spec(self):
        spec = ToolSpec(name="uv", version="0.5.11")
        assert spec.name == "uv"
        assert spec.version == "0.5.11"

    def test_tool_spec_equality(self):
        spec1 = ToolSpec(name="python", version="3.12")
        spec2 = ToolSpec(name="python", version="3.12")
        assert spec1 == spec2

    def test_tool_spec_inequality(self):
        spec1 = ToolSpec(name="python", version="3.12")
        spec2 = ToolSpec(name="python", version="3.11")
        assert spec1 != spec2


class TestGenerateMiseToml:
    def test_generate_with_tools_only(self):
        tools = [
            ToolSpec(name="uv", version="0.5.11"),
            ToolSpec(name="python", version="3.12"),
        ]
        result = generate_mise_toml(tools=tools)

        assert "[tools]" in result
        assert 'uv = "0.5.11"' in result
        assert 'python = "3.12"' in result

    def test_generate_with_env(self):
        tools = [ToolSpec(name="uv", version="0.5.11")]
        env = {"UV_INDEX_URL": "http://localhost:3141/simple"}

        result = generate_mise_toml(tools=tools, env=env)

        assert "[env]" in result
        assert 'UV_INDEX_URL = "http://localhost:3141/simple"' in result

    def test_generate_with_task(self):
        tools = [ToolSpec(name="node", version="22")]
        task_command = "npx @cyclonedx/cdxgen -o output.json project/"

        result = generate_mise_toml(tools=tools, task_name="sca", task_command=task_command)

        assert "[tasks.sca]" in result
        assert f'run = "{task_command}"' in result

    def test_generate_empty_tools(self):
        result = generate_mise_toml(tools=[])
        assert result.strip() == ""

    def test_generate_full_config(self):
        tools = [
            ToolSpec(name="uv", version="0.5.11"),
            ToolSpec(name="python", version="3.12"),
            ToolSpec(name="node", version="22"),
        ]
        env = {"UV_INDEX_URL": "http://localhost:3141/simple"}
        task_command = "cdxgen -o /tmp/out.json /tmp/project"

        result = generate_mise_toml(
            tools=tools,
            env=env,
            task_name="sca",
            task_command=task_command,
        )

        assert "[tools]" in result
        assert "[env]" in result
        assert "[tasks.sca]" in result


class TestMiseRunner:
    def test_create_runner(self, tmp_path: Path):
        runner = MiseRunner(cwd=tmp_path)
        assert runner.cwd == tmp_path

    def test_run_task_mise_not_found(self, tmp_path: Path, monkeypatch):
        runner = MiseRunner(cwd=tmp_path)
        monkeypatch.setattr("shutil.which", lambda x: None)

        result = runner.run_task("sca", timeout=10)

        assert not result.success
        assert result.error_message is not None
        assert "mise" in result.error_message.lower()

    def test_run_task_returns_result(self, tmp_path: Path):
        runner = MiseRunner(cwd=tmp_path)

        # Create a mise.toml with a simple task
        mise_toml = tmp_path / "mise.toml"
        mise_toml.write_text('[tasks.test]\nrun = "echo hello"\n')

        result = runner.run_task("test", timeout=10)

        # Result should have expected fields regardless of success
        assert hasattr(result, "success")
        assert hasattr(result, "exit_code")
        assert hasattr(result, "stdout")
        assert hasattr(result, "stderr")
        assert hasattr(result, "duration_seconds")
        assert hasattr(result, "error_message")

    def test_trust_mise_toml(self, tmp_path: Path):
        runner = MiseRunner(cwd=tmp_path)

        # Create a mise.toml
        mise_toml = tmp_path / "mise.toml"
        mise_toml.write_text('[tools]\npython = "3.12"\n')

        # trust() should return bool
        result = runner.trust()
        assert isinstance(result, bool)

    def test_write_mise_toml(self, tmp_path: Path):
        runner = MiseRunner(cwd=tmp_path)
        tools = [ToolSpec(name="python", version="3.12")]

        runner.write_mise_toml(tools=tools)

        mise_toml = tmp_path / "mise.toml"
        assert mise_toml.exists()
        content = mise_toml.read_text()
        assert 'python = "3.12"' in content

    def test_run_task_sets_mise_ceiling_paths(self, tmp_path: Path):
        """Verify MISE_CEILING_PATHS is set to sandbox directory for isolation."""
        runner = MiseRunner(cwd=tmp_path)

        with patch("bom_bench.sandbox.mise.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            runner.run_task("test")

            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args.kwargs
            assert "env" in call_kwargs
            assert "MISE_CEILING_PATHS" in call_kwargs["env"]
            assert call_kwargs["env"]["MISE_CEILING_PATHS"] == str(tmp_path)

    def test_trust_sets_mise_ceiling_paths(self, tmp_path: Path):
        """Verify MISE_CEILING_PATHS is set during trust operation."""
        runner = MiseRunner(cwd=tmp_path)

        with patch("bom_bench.sandbox.mise.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            runner.trust()

            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args.kwargs
            assert "env" in call_kwargs
            assert "MISE_CEILING_PATHS" in call_kwargs["env"]
            assert call_kwargs["env"]["MISE_CEILING_PATHS"] == str(tmp_path)
