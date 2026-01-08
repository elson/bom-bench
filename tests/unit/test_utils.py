"""Tests for utility functions."""

from bom_bench.utils import expandvars_dict


class TestExpandvarsDict:
    """Tests for expandvars_dict function."""

    def test_expands_simple_var(self, monkeypatch):
        monkeypatch.setenv("MY_VAR", "hello")
        result = expandvars_dict({"key": "$MY_VAR"})
        assert result["key"] == "hello"

    def test_expands_braced_var(self, monkeypatch):
        monkeypatch.setenv("MY_VAR", "hello")
        result = expandvars_dict({"key": "${MY_VAR}"})
        assert result["key"] == "hello"

    def test_expands_var_with_default(self, monkeypatch):
        monkeypatch.delenv("MISSING_VAR", raising=False)
        result = expandvars_dict({"key": "${MISSING_VAR:-default_value}"})
        assert result["key"] == "default_value"

    def test_expands_var_with_default_when_set(self, monkeypatch):
        monkeypatch.setenv("EXISTS", "actual")
        result = expandvars_dict({"key": "${EXISTS:-default}"})
        assert result["key"] == "actual"

    def test_expands_nested_dicts(self, monkeypatch):
        monkeypatch.setenv("HOST", "localhost")
        monkeypatch.setenv("PORT", "8080")
        data = {"server": {"host": "$HOST", "port": "$PORT"}}
        result = expandvars_dict(data)
        assert result["server"]["host"] == "localhost"
        assert result["server"]["port"] == "8080"

    def test_expands_lists(self, monkeypatch):
        monkeypatch.setenv("DIR", "/project")
        monkeypatch.setenv("OUT", "/output")
        data = {"args": ["scan", "$DIR", "-o", "$OUT"]}
        result = expandvars_dict(data)
        assert result["args"] == ["scan", "/project", "-o", "/output"]

    def test_preserves_non_strings(self):
        data = {"count": 42, "enabled": True, "ratio": 3.14, "items": None}
        result = expandvars_dict(data)
        assert result["count"] == 42
        assert result["enabled"] is True
        assert result["ratio"] == 3.14
        assert result["items"] is None

    def test_no_vars_unchanged(self):
        result = expandvars_dict({"key": "plain string"})
        assert result["key"] == "plain string"

    def test_multiple_vars_in_string(self, monkeypatch):
        monkeypatch.setenv("FIRST", "one")
        monkeypatch.setenv("SECOND", "two")
        result = expandvars_dict({"key": "$FIRST and $SECOND"})
        assert result["key"] == "one and two"
