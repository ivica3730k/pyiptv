from abc import ABC, abstractmethod


class BasePlayer(ABC):
    @abstractmethod
    def play(self, url: str):
        pass
