import aiohttp
import asyncio
import logging
from contextlib import suppress
from cryptomate.market.feed import Feed, FeedEvent
from cryptomate.market.feed.binance.depth import DepthStream
from cryptomate.market.feed.binance.tick import TickStream

logger = logging.getLogger(__name__)


class BinanceFeed(Feed):
    ''' Provide ticks and order book updates from https://www.binance.com/

    :ivar callable callback: a function invoked on every event.
                             Has form ``callback(feed, symbol, event, *, data)``
    :ivar callable on_error: invoked when an enabled event stream gets an error condition.
                             Has form ``on_error(feed, symbol, event, *, exc, retry, msg)``
    :param session: aiohttp session to use to connect to the stream.
    :type session: aiohttp.ClientSession or None
    '''
    name = 'binance'
    __slots__ = ('_session', '_own_session', '_streams', '_close_task', '_closing_streams')

    def __init__(self, *, callback, on_error, session=None):
        super().__init__(callback=callback, on_error=on_error)
        if session:
            self._session, self._own_session = session, False
        else:
            self._session, self._own_session = aiohttp.ClientSession(), True

        self._streams = {}                      # (symbol, event) => obj
        self._close_task = None                 # shutdown task
        self._closing_streams = []              # streams with close() called but not yet complete

    def close(self):
        if not self._close_task:
            self._close_task = asyncio.ensure_future(self._do_close())

    async def _do_close(self):
        ''' Asynchronous task started by :meth:`close` '''

        to_wait = self._closing_streams
        for stream in self._streams.values():
            stream.close()
            to_wait.append(stream)
        self._streams.clear()

        if to_wait:
            await asyncio.wait([stream.wait_closed() for stream in to_wait])
            to_wait.clear()

        if self._own_session:
            await self._session.close()

    async def wait_closed(self):
        await self._close_task

    async def enable(self, symbol, event):
        key = (symbol, event)
        assert not self._close_task, 'calling enable() after close() is a bug'
        assert key not in self._streams, 'enabling a stream already enabled is a bug'

        if event == FeedEvent.TICK:
            stream = TickStream(symbol, on_tick=self._handle_tick,
                                on_error=self._handle_error, session=self._session)
        elif event == FeedEvent.ORDERBOOK:
            stream = DepthStream(symbol, on_update=self._handle_orderbook,
                                on_error=self._handle_error, session=self._session)
        else:
            raise ValueError('Unknown event type %s' % event)

        self._streams[key] = stream
        try:
            await stream.start()
        except Exception as exc:
            with suppress(KeyError):    # happens if disable() called before enable() completes
                del self._streams[key]
            raise exc

    async def disable(self, symbol, event):
        stream = self._streams.pop((symbol, event))
        stream.close()
        self._closing_streams.append(stream)
        await stream.wait_closed()
        self._closing_streams.remove(stream)

    def _handle_error(self, feed, exc, exc_info):
        logger.error('in binance worker for %s [%s]: %s', feed.symbol, feed.event.name, exc, exc_info=exc_info)
        del self._streams[feed.symbol, feed.event]
        self.on_error(self, feed.symbol, feed.event, exc=exc, msg=str(exc), retry=0)

    def _handle_tick(self, feed, data):
        self.callback(self, feed.symbol, feed.event, data=data)

    def _handle_orderbook(self, feed, data):
        self.callback(self, feed.symbol, feed.event, data=data)
