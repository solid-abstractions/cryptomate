from abc import ABC, abstractmethod
from enum import Enum, auto


class FeedEvent(Enum):
    TICK = auto()       #: tick event stream
    ORDERBOOK = auto()  #: orderbook updates event stream


class Feed(ABC):
    ''' Abstraction of a single market data feed

    :cvar str name: feed name, for use in feed descriptions.
    :ivar callable callback: a function invoked on every event.
                             Has form ``callback(feed, symbol, event, data)``
    :ivar callable on_error: invoked when an enabled event stream gets an error condition.
                             Has form ``on_error(feed, symbol, event, exc=None, retry, msg)``
    '''

    name = None
    __slots__ = ('callback', 'on_error')

    def __init__(self, *, callback, on_error):
        if not callable(callback):
            raise TypeError('callback must be callable')
        if not callable(on_error):
            raise TypeError('erorr handler must be callable')
        self.callback = callback
        self.on_error = on_error

    @abstractmethod
    def close(self):
        ''' Request feed shutdown '''
        raise NotImplementedError

    @abstractmethod
    async def wait_closed(self):
        ''' Wait until feed is completely shutdown.
            Only valid after :meth:`close` has been called.
        '''
        raise NotImplementedError

    @abstractmethod
    async def enable(self, symbol, event):
        ''' Enable an even stream.

        A stream may only be enabled once. Enabling a feed already enabled is a bug.

        :param str symbol: Market symbol. Actual meaning depends on platform.
        :param FeedEvent event: Event stream to enable.
        '''
        raise NotImplementedError

    @abstractmethod
    async def disable(self, symbol, event):
        ''' Disable an even stream.

        A stream may only be disabled if it is enabled.

        :param str symbol: Market symbol. Actual meaning depends on platform.
        :param FeedEvent event: Event stream to enable.
        '''
        raise NotImplementedError
