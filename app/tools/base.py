from abc import ABC, abstractmethod


class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    def execute(self, **kwargs) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def schema(self) -> dict:
        raise NotImplementedError
