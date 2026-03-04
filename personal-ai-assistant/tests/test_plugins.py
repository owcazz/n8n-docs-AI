"""Tests for the plugin system."""

import pytest

from plugins.base import PluginRegistry, ToolResult


async def dummy_handler(user_id: int, **kwargs) -> ToolResult:
    return ToolResult(content=f"ok: {kwargs}")


def test_registry_register_and_get():
    registry = PluginRegistry()
    registry.register_tool(
        name="test_tool",
        description="A test tool",
        parameters={"type": "object", "properties": {}},
        handler=dummy_handler,
    )
    assert "test_tool" in registry.tools
    assert registry.get_handler("test_tool") is dummy_handler
    assert registry.get_handler("nonexistent") is None


def test_tool_result_format():
    result = ToolResult(content="Hello")
    assert result.to_api_format() == "Hello"
    assert result.is_error is False

    error = ToolResult(content="Oops", is_error=True)
    assert error.is_error is True


def test_youtube_extract_video_id():
    from plugins.youtube import _extract_video_id

    assert _extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert _extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert _extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert _extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42") == "dQw4w9WgXcQ"
    assert _extract_video_id("not a url") is None
