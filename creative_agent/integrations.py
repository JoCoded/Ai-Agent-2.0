"""Deliberately opt-in read-only tool gateway for future MCP client adapters.

This is an adapter contract, NOT a live MCP SDK/server connection. Any real
client needs explicit configuration, authentication, consent and tests.
"""
from typing import Any, Callable


class ToolAccessError(ValueError):
    pass


class ReadOnlyGateway:
    """No publishing, writes, or arbitrary remote tool execution permitted."""

    def __init__(self, allowed_tools: dict[str, Callable[[dict], Any]] | None = None):
        self._allowed = dict(allowed_tools or {})
        for name in self._allowed:
            if not name.startswith("read_"):
                raise ToolAccessError("only read_ tools may be registered")

    def invoke(self, name: str, arguments: dict, *, consent: bool = False) -> Any:
        if not consent:
            raise ToolAccessError("explicit per-call consent is required")
        if name not in self._allowed:
            raise ToolAccessError("tool is not allowlisted")
        if not isinstance(arguments, dict):
            raise ToolAccessError("arguments must be an object")
        if len(str(arguments)) > 4000:
            raise ToolAccessError("tool arguments too large")
        return self._allowed[name](dict(arguments))
