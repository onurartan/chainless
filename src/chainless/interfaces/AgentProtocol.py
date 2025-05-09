from typing import Protocol, runtime_checkable
from abc import abstractmethod


@runtime_checkable
class AgentProtocol(Protocol):
    name: str

    @abstractmethod
    def start(self, input: str, verbose: bool = False, **kwargs) -> dict: ...
