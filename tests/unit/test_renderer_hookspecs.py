"""Tests for renderer hook specifications."""

import pluggy

from bom_bench.plugins.hookspecs import RendererSpec


class TestRendererHookspecs:
    """Tests for renderer hook specifications."""

    def test_renderer_spec_has_sca_tool_hook(self):
        """Test that RendererSpec defines register_sca_tool_result_renderer hook."""
        assert hasattr(RendererSpec, "register_sca_tool_result_renderer")

    def test_renderer_spec_has_benchmark_hook(self):
        """Test that RendererSpec defines register_benchmark_result_renderer hook."""
        assert hasattr(RendererSpec, "register_benchmark_result_renderer")

    def test_hooks_can_be_registered(self):
        """Test that renderer hooks can be registered with plugin manager."""
        pm = pluggy.PluginManager("bom_bench")
        pm.add_hookspecs(RendererSpec)

        # Verify hooks are registered
        assert "register_sca_tool_result_renderer" in pm.hook.__dict__
        assert "register_benchmark_result_renderer" in pm.hook.__dict__

    def test_sca_tool_hook_signature(self):
        """Test that SCA tool renderer hook has correct signature."""
        import inspect

        sig = inspect.signature(RendererSpec.register_sca_tool_result_renderer)
        params = list(sig.parameters.keys())

        assert "self" in params
        assert "bom_bench" in params
        assert "tool_name" in params
        assert "summaries" in params

    def test_benchmark_hook_signature(self):
        """Test that benchmark renderer hook has correct signature."""
        import inspect

        sig = inspect.signature(RendererSpec.register_benchmark_result_renderer)
        params = list(sig.parameters.keys())

        assert "self" in params
        assert "bom_bench" in params
        assert "overall_summaries" in params
        assert "summaries" in params
