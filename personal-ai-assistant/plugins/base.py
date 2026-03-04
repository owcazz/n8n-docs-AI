"""Base plugin system - tool registration and dispatch."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result returned by a tool execution."""
    content: str
    is_error: bool = False
    metadata: dict = field(default_factory=dict)

    def to_api_format(self) -> str:
        return self.content


ToolHandler = Callable[..., Coroutine[Any, Any, ToolResult]]


class PluginRegistry:
    """Central registry for all plugin tools."""

    def __init__(self):
        self.tools: dict[str, dict] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: ToolHandler,
    ):
        """Register a tool with its schema and handler."""
        self.tools[name] = {
            "description": description,
            "parameters": parameters,
        }
        self._handlers[name] = handler
        logger.info("Registered tool: %s", name)

    def get_handler(self, name: str) -> ToolHandler | None:
        return self._handlers.get(name)


class BasePlugin:
    """Base class for all plugins."""

    name: str = "base"

    def __init__(self, registry: PluginRegistry, **kwargs):
        self.registry = registry
        self.setup(**kwargs)

    def setup(self, **kwargs):
        """Override to configure the plugin and register tools."""
        raise NotImplementedError
