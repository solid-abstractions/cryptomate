import aiohttp
import asyncio
import logging
from decimal import Decimal
from cryptomate.market.data import Tick
from cryptomate.market.feed import Feed
from cryptomate.util.worker import worker

logger = logging.getLogger(__name__)


class BinanceFeed(Feed):
    name = 'binance'
    WS_URL = 'wss://stream.binance.com:9443/stream?streams={streams}'

    def __init__(self, callback, session=None):
        super().__init__(callback)
        if session:
            self._session, self._own_session = session, False
        else:
            self._session, self._own_session = aiohttp.ClientSession(), True
        self._streams = {}          # idstring => description
        self._starting_task = None  # worker in startup phase
        self._task = None           # worker in running phase
        self._started = None        # future that resolves when worker completes startup
        self._close_task = None     # shutdown task

    @classmethod
    def create(cls, description, callback):
        return cls(callback)

    def close(self):
        if self._starting_task:
            self._starting_task.cancel()
        if self._task and not self._task.done():
            self._task.cancel()
        if self._session and self._own_session:
            self._close_task = asyncio.ensure_future(self._session.close())

    async def wait_closed(self):
        if self._task:
            await self._task
        if self._close_task:
            await self._close_task

    @worker(restart=1, restart_on_exception=15)
    async def _worker(self):
        url = self.WS_URL.format(streams='/'.join(self._streams.keys()))
        logger.info('connecting to <%s>' % url)

        async with self._session.ws_connect(url, heartbeat=60) as ws:
            if asyncio.Task.current_task() == self._starting_task:
                if self._task and not self._task.done():
                    self._task.cancel()
                self._started.set_result(None)
                self._starting_task, self._task = None, self._starting_task
            async for message in ws:
                if message.type == aiohttp.WSMsgType.TEXT:
                    self._process(message.json())

    def _process(self, data):
        stream, data = data['stream'], data['data']

        self.callback(self._streams[stream], Tick(
            id=data['t'],
            timestamp=data['E'],
            type='sell' if data['m'] else 'buy',
            amount=Decimal(data['q']),
            price=Decimal(data['p']),
        ))

    def _restart_worker(self):
        if self._starting_task:
            self._starting_task.cancel()

        self._started = asyncio.Future()
        if self._streams:
            self._starting_task = asyncio.ensure_future(self._worker())
        else:
            self._task.cancel()
            self._started.set_result(None)

    async def enable(self, description):
        stream = '{description.symbol}@trade'.format(description=description)
        self._streams[stream] = description
        self._restart_worker()
        await self._started

    async def disable(self, description):
        stream = '{description.symbol}@trade'.format(description=description)
        del self._streams[stream]
        self._restart_worker()
        await self._started
