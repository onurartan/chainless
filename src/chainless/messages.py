import time
from typing import Any, List
from dataclasses import dataclass, field

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    UserPromptPart,
    SystemPromptPart,
    TextPart,
)

import chainless._utils as _utils


def to_pydantic(messages: List) -> List:
    """Convert simple messages to pydantic_ai ModelRequest / ModelResponse."""
    converted = []
    for msg in messages:
        if isinstance(msg, UserMessage):
            converted.append(ModelRequest(parts=[UserPromptPart(content=msg.content)]))
        elif isinstance(msg, AssistantMessage):
            converted.append(ModelResponse(parts=[TextPart(content=msg.content)]))
        elif isinstance(msg, SystemMessage):
            converted.append(
                ModelRequest(parts=[SystemPromptPart(content=msg.content)])
            )
    return converted


def from_pydantic(messages: List) -> List:
    """Convert pydantic_ai ModelRequest / ModelResponse to simple messages."""
    converted = []
    for msg in messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, UserPromptPart):
                    converted.append(UserMessage(content=part.content))
                elif isinstance(part, SystemPromptPart):
                    converted.append(SystemMessage(content=part.content))
        elif isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, TextPart):
                    converted.append(AssistantMessage(content=part.content))
    return converted


@dataclass(repr=False)
class UserMessage:
    """A message sent by the user."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    __repr__ = _utils.dataclasses_no_defaults_repr


@dataclass(repr=False)
class AssistantMessage:
    """A message sent by the assistant/model."""

    content: str
    timestamp: float = field(default_factory=time.time)

    __repr__ = _utils.dataclasses_no_defaults_repr


@dataclass(repr=False)
class SystemMessage:
    """A system message providing context or instructions."""

    content: str
    role: str = "system"
    timestamp: float = field(default_factory=time.time)

    __repr__ = _utils.dataclasses_no_defaults_repr


__all__ = ["UserMessage", "AssistantMessage", "SystemMessage"]
