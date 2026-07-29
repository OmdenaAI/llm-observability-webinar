"""Entities related to MCP tool calls."""
from dataclasses import dataclass, field
from enum import Enum


class ToolCallStatus(str, Enum):
    """The outcome of a single MCP tool invocation."""

    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True)
class ToolCallResult:
    """The result of a single MCP tool invocation, shaped for tracing.

    Attributes:
        tool_name: The name of the MCP tool that was called (e.g.
            "sprints_get_active").
        arguments: The arguments passed to the tool.
        result: The raw result returned by the tool, or None on failure.
        status: Whether the call succeeded or failed.
        latency_ms: Wall-clock time the call took, in milliseconds.
        error_message: The error message if the call failed, otherwise
            None.
        metadata: Any additional call-specific data.
    """

    tool_name: str
    arguments: dict
    result: dict | None
    status: ToolCallStatus
    latency_ms: float
    error_message: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ToolChain:
    """An ordered sequence of tool calls made to answer a single question.

    Attributes:
        calls: The individual tool calls, in the order they were made.
    """

    calls: list[ToolCallResult]

    @property
    def all_succeeded(
        self,
    ) -> bool:
        """Return True if every call in the chain succeeded."""
        return all(
            call.status == ToolCallStatus.SUCCESS
            for call in self.calls
        )
