
class Feed:
    name = None

    def __init__(self, callback):
        self.callback = callback

    @classmethod
    def create(self, description, callback):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    async def wait_closed(self):
        raise NotImplementedError

    async def enable(self, description):
        raise NotImplementedError

    async def disable(self, description):
        raise NotImplementedError
