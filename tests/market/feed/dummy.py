import asyncio
from cryptomate.market.feed import Feed, register


@register
class DummyFeed(Feed):
    ''' Market feed that accepts all descriptions
        and allows emulating tick events
    '''
    name = 'dummy'
    __slots__ = ('_enabled', '_closed')

    def __init__(self, *, callback, on_error):
        super().__init__(callback=callback, on_error=on_error)
        self._enabled = []
        self._closed = asyncio.Event()

    # Feed interface

    def close(self):
        assert not self._closed.is_set(), 'attempt to close feed twice'
        self._closed.set()

    async def wait_closed(self):
        await self._closed.wait()

    async def enable(self, symbol, event):
        assert not self._closed.is_set(), 'attempt to enable event on closed feed'
        key = (symbol, event)
        if not key in self._enabled:
            self._enabled.append(key)

    async def disable(self, symbol, event):
        assert not self._closed.is_set(), 'attempt to disable event on closed feed'
        key = (symbol, event)
        self._enabled.remove(key)

    # Debugging tools

    @property
    def enabled(self):
        return tuple(self._enabled)

    @property
    def closed(self):
        return self._closed.is_set()

    def generate_event(self, symbol, event, **kwargs):
        assert not self._closed.is_set(), 'attempt to generate event on closed feed'
        assert (symbol, event) in self._enabled, 'attempt to generate event on disabled market'
        self.callback(self, symbol, event=event, **kwargs)

    def generate_error(self, symbol, event, **kwargs):
        assert not self._closed.is_set(), 'attempt to generate error on closed feed'
        assert (symbol, event) in self._enabled, 'attempt to generate error on disabled market'
        self.on_error(self, symbol, event=event, **kwargs)

    def __repr__(self):
        enabled = ('CLOSED' if self._closed.is_set() else
                   ', '.join(f'{symbol} [{event.name.lower()}]'
                             for symbol, event in self._enabled))
        return (f'{self.__class__.__name__}('
                f'[{enabled}], '
                f'callback={self.callback}, '
                f'on_error={self.on_error})')
