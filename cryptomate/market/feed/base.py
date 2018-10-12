from abc import ABC, abstractmethod


class Feed(ABC):
    name = None

    def __init__(self, callback):
        self.callback = callback

    @classmethod
    @abstractmethod
    def create(self, description, callback):
        raise NotImplementedError

    @abstractmethod
    def close(self):
        raise NotImplementedError

    @abstractmethod
    async def wait_closed(self):
        raise NotImplementedError

    @abstractmethod
    async def enable(self, description):
        raise NotImplementedError

    @abstractmethod
    async def disable(self, description):
        raise NotImplementedError
