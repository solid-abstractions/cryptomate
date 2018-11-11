import aiohttp
import asyncio
import json
import logging
import sys
from abc import ABCMeta, abstractmethod
from contextlib import suppress
from cryptomate.market.feed import (FeedConnectionError, FeedPayloadError)

logger = logging.getLogger(__name__)

WS_URL = 'wss://stream.binance.com:9443/ws/{stream}'

# ----------------------------------------------------------------------------

class Stream(metaclass=ABCMeta):
    ''' Abstract worker that receives event from a market stream

    :param session: aiohttp session to use to connect to the stream.
    :type session: aiohttp.ClientSession
    :param on_error: initial value for ``on_error``.
    :ivar on_error: callback to invoke on stream errors, in form
                    ``on_error(feed, exc, exc_info)``.
    '''

    HEARTBEAT = 60
    __slots__ = ('_session', '_worker_task', 'on_error')

    def __init__(self, *, session, on_error):
        self._session = session
        self._worker_task = None
        self.on_error = on_error

    @property
    @abstractmethod
    def _name(self):
        raise NotImplementedError

    async def start(self):
        ready = asyncio.Event()
        self._worker_task = asyncio.ensure_future(self._worker(ready=ready))

        # Wait until worker is ready or has failed
        try:
            wait_ready = asyncio.ensure_future(ready.wait())
            done, pending = await asyncio.wait(
                [self._worker_task, wait_ready],
                return_when=asyncio.FIRST_COMPLETED,
            )
        except asyncio.CancelledError as exc:
            self._worker_task.cancel()
            wait_ready.cancel()
            with suppress(asyncio.CancelledError):
                await self._worker_task     # let worker shutdown
            raise exc

        # if event is not set, worker failed to start
        if not ready.is_set():
            wait_ready.cancel()

            self._worker_task.result()
            assert False, 'worker must propagate the exception'

    def close(self):
        ''' Signal the worker to stop '''
        assert self._worker_task, 'close() is only valid after a start()'
        self._worker_task.cancel()

    async def wait_closed(self):
        ''' Wait until the worker has stopped '''
        assert self._worker_task, 'wait_closed() is only valid after a start()'
        with suppress(asyncio.CancelledError):
            await self._worker_task

    async def _worker(self, *, ready):
        ws = await self._connect()

        try:
            ready.set()
            del ready
            while True:
                data = await self._receive(ws)
                event = self._decode(data)
                self._process(event)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self.on_error(self, exc, sys.exc_info())
        finally:
            await ws.close()

    async def _connect(self):
        ''' Establish connection to stream server

        :return: connected websocket
        :rtype: aiohttp.ClientWebSocketResponse
        '''
        url = WS_URL.format(stream=self._name)
        logger.info('connecting to <%s>' % url)
        try:
            return await self._session.ws_connect(url, heartbeat=self.HEARTBEAT)
        except aiohttp.ClientError as exc:
            raise FeedConnectionError('could not connect to websocket') from exc

    async def _receive(self, ws):
        ''' Wait until a json frame is received from the server

        :param aiohttp.ClientWebSocketResponse ws: open websocket.
        :return: decoded json frame.
        :rtype: dict
        '''
        try:
            message = await ws.receive()
        except aiohttp.ClientError as exc:
            raise FeedConnectionError(str(exc)) from exc
        if message.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSED):
            raise FeedConnectionError('connection closed')
        try:
            data = message.json()
        except json.JSONDecodeError as exc:
            raise FeedPayloadError('received invalid json') from exc
        return data

    @abstractmethod
    def _decode(self, data):
        ''' Decode raw data into a complete event '''
        raise NotImplementedError

    @abstractmethod
    def _process(self, event):
        ''' Do something useful with event, such as invoking callbacks '''
        raise NotImplementedError
