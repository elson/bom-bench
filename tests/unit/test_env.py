"""Tests for environment variable handling and interpolation."""

from pathlib import Path

import pytest


class TestLoadDotenv:
    """Tests for loading .env files."""

    def test_load_env_file(self, tmp_path: Path):
        """Test loading variables from a .env file."""
        from bom_bench.env import load_dotenv

        env_file = tmp_path / ".env"
        env_file.write_text("MY_VAR=hello\nOTHER_VAR=world\n")

        env = load_dotenv(env_file)

        assert env["MY_VAR"] == "hello"
        assert env["OTHER_VAR"] == "world"

    def test_load_env_file_with_quotes(self, tmp_path: Path):
        """Test loading variables with quoted values."""
        from bom_bench.env import load_dotenv

        env_file = tmp_path / ".env"
        env_file.write_text("QUOTED=\"value with spaces\"\nSINGLE='single quoted'\n")

        env = load_dotenv(env_file)

        assert env["QUOTED"] == "value with spaces"
        assert env["SINGLE"] == "single quoted"

    def test_load_env_file_ignores_comments(self, tmp_path: Path):
        """Test that comments are ignored."""
        from bom_bench.env import load_dotenv

        env_file = tmp_path / ".env"
        env_file.write_text("# This is a comment\nVAR=value\n# Another comment\n")

        env = load_dotenv(env_file)

        assert "VAR" in env
        assert env["VAR"] == "value"
        assert "#" not in "".join(env.keys())

    def test_load_env_file_ignores_empty_lines(self, tmp_path: Path):
        """Test that empty lines are ignored."""
        from bom_bench.env import load_dotenv

        env_file = tmp_path / ".env"
        env_file.write_text("VAR1=value1\n\n\nVAR2=value2\n")

        env = load_dotenv(env_file)

        assert len(env) == 2
        assert env["VAR1"] == "value1"
        assert env["VAR2"] == "value2"

    def test_load_env_file_not_found(self, tmp_path: Path):
        """Test that missing .env file returns empty dict."""
        from bom_bench.env import load_dotenv

        env_file = tmp_path / ".env"

        env = load_dotenv(env_file)

        assert env == {}

    def test_load_env_file_with_equals_in_value(self, tmp_path: Path):
        """Test values containing equals signs."""
        from bom_bench.env import load_dotenv

        env_file = tmp_path / ".env"
        env_file.write_text("URL=https://example.com?foo=bar&baz=qux\n")

        env = load_dotenv(env_file)

        assert env["URL"] == "https://example.com?foo=bar&baz=qux"


class TestInterpolateValue:
    """Tests for variable interpolation in strings."""

    def test_interpolate_simple_var(self, monkeypatch):
        """Test interpolating a simple variable."""
        from bom_bench.env import interpolate_value

        monkeypatch.setenv("MY_VAR", "hello")

        result = interpolate_value("${MY_VAR}")

        assert result == "hello"

    def test_interpolate_var_in_string(self, monkeypatch):
        """Test interpolating variable embedded in string."""
        from bom_bench.env import interpolate_value

        monkeypatch.setenv("NAME", "world")

        result = interpolate_value("hello ${NAME}!")

        assert result == "hello world!"

    def test_interpolate_multiple_vars(self, monkeypatch):
        """Test interpolating multiple variables."""
        from bom_bench.env import interpolate_value

        monkeypatch.setenv("FIRST", "one")
        monkeypatch.setenv("SECOND", "two")

        result = interpolate_value("${FIRST} and ${SECOND}")

        assert result == "one and two"

    def test_interpolate_with_default(self, monkeypatch):
        """Test interpolating with default value when var not set."""
        from bom_bench.env import interpolate_value

        monkeypatch.delenv("MISSING_VAR", raising=False)

        result = interpolate_value("${MISSING_VAR:-default_value}")

        assert result == "default_value"

    def test_interpolate_with_default_var_exists(self, monkeypatch):
        """Test that default is not used when var exists."""
        from bom_bench.env import interpolate_value

        monkeypatch.setenv("EXISTS", "actual")

        result = interpolate_value("${EXISTS:-default}")

        assert result == "actual"

    def test_interpolate_missing_var_raises(self, monkeypatch):
        """Test that missing var without default raises error."""
        from bom_bench.env import interpolate_value

        monkeypatch.delenv("MISSING_VAR", raising=False)

        with pytest.raises(ValueError, match="Environment variable 'MISSING_VAR' is not set"):
            interpolate_value("${MISSING_VAR}")

    def test_interpolate_no_vars(self):
        """Test string without variables is unchanged."""
        from bom_bench.env import interpolate_value

        result = interpolate_value("plain string")

        assert result == "plain string"

    def test_interpolate_empty_default(self, monkeypatch):
        """Test empty default value."""
        from bom_bench.env import interpolate_value

        monkeypatch.delenv("MISSING", raising=False)

        result = interpolate_value("prefix${MISSING:-}suffix")

        assert result == "prefixsuffix"

    def test_interpolate_with_env_dict(self, monkeypatch):
        """Test interpolating with additional env dict."""
        from bom_bench.env import interpolate_value

        monkeypatch.delenv("FROM_DICT", raising=False)
        env = {"FROM_DICT": "dict_value"}

        result = interpolate_value("${FROM_DICT}", env=env)

        assert result == "dict_value"

    def test_interpolate_env_dict_overrides_os_env(self, monkeypatch):
        """Test that env dict takes precedence over os.environ."""
        from bom_bench.env import interpolate_value

        monkeypatch.setenv("VAR", "from_os")
        env = {"VAR": "from_dict"}

        result = interpolate_value("${VAR}", env=env)

        assert result == "from_dict"


class TestInterpolateDict:
    """Tests for interpolating all values in a dictionary."""

    def test_interpolate_dict_shallow(self, monkeypatch):
        """Test interpolating values in a flat dict."""
        from bom_bench.env import interpolate_dict

        monkeypatch.setenv("TOKEN", "secret123")

        data = {"api_key": "${TOKEN}", "name": "test"}
        result = interpolate_dict(data)

        assert result["api_key"] == "secret123"
        assert result["name"] == "test"

    def test_interpolate_dict_nested(self, monkeypatch):
        """Test interpolating values in nested dicts."""
        from bom_bench.env import interpolate_dict

        monkeypatch.setenv("HOST", "localhost")
        monkeypatch.setenv("PORT", "8080")

        data = {
            "server": {
                "host": "${HOST}",
                "port": "${PORT}",
            }
        }
        result = interpolate_dict(data)

        assert result["server"]["host"] == "localhost"
        assert result["server"]["port"] == "8080"

    def test_interpolate_dict_with_list(self, monkeypatch):
        """Test interpolating values in lists within dict."""
        from bom_bench.env import interpolate_dict

        monkeypatch.setenv("DIR", "/project")
        monkeypatch.setenv("OUT", "/output")

        data = {"args": ["scan", "${DIR}", "-o", "${OUT}"]}
        result = interpolate_dict(data)

        assert result["args"] == ["scan", "/project", "-o", "/output"]

    def test_interpolate_dict_preserves_non_strings(self, monkeypatch):
        """Test that non-string values are preserved."""
        from bom_bench.env import interpolate_dict

        data = {"count": 42, "enabled": True, "ratio": 3.14, "items": None}
        result = interpolate_dict(data)

        assert result["count"] == 42
        assert result["enabled"] is True
        assert result["ratio"] == 3.14
        assert result["items"] is None


class TestGetProjectEnv:
    """Tests for getting combined env from .env file and OS."""

    def test_get_project_env_combines_sources(self, tmp_path: Path, monkeypatch):
        """Test that project env combines .env file and OS env."""
        from bom_bench.env import get_project_env

        env_file = tmp_path / ".env"
        env_file.write_text("FROM_FILE=file_value\n")
        monkeypatch.setenv("FROM_OS", "os_value")

        env = get_project_env(tmp_path)

        assert env["FROM_FILE"] == "file_value"
        assert env["FROM_OS"] == "os_value"

    def test_get_project_env_dotenv_overrides_os(self, tmp_path: Path, monkeypatch):
        """Test that .env file values override OS env."""
        from bom_bench.env import get_project_env

        env_file = tmp_path / ".env"
        env_file.write_text("SHARED=from_file\n")
        monkeypatch.setenv("SHARED", "from_os")

        env = get_project_env(tmp_path)

        assert env["SHARED"] == "from_file"
