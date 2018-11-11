import aiohttp
import asyncio
import itertools
import sys
from contextlib import suppress
from decimal import Decimal, DecimalException
from cryptomate.market.data import OrderUpdate
from cryptomate.market.feed import FeedEvent, FeedConnectionError, FeedPayloadError, FeedRemoteError
from cryptomate.market.feed.binance.stream import Stream

DEPTH_URL = 'https://www.binance.com/api/v1/depth?symbol={symbol}&limit=1000'


class DepthStream(Stream):
    ''' Worker that receives events from a market depth stream '''

    event = FeedEvent.ORDERBOOK
    __slots__ = ('symbol', 'on_update')

    def __init__(self, symbol, *, on_update, **kwargs):
        super().__init__(**kwargs)
        self.symbol = symbol
        self.on_update = on_update

    @property
    def _name(self):
        return f'{self.symbol}@depth'

    async def _worker(self, *, ready):
        ws = await self._connect()

        try:
            # Buffer events while we fetch an order book snapshot
            buffer_task = asyncio.ensure_future(self._buffer_events(ws))
            fetch_task = asyncio.ensure_future(self._fetch_snapshot())
            try:
                await asyncio.wait([buffer_task, fetch_task], return_when=asyncio.FIRST_COMPLETED)
            except asyncio.CancelledError:
                buffer_task.cancel()
                fetch_task.cancel()
                await asyncio.gather(buffer_task, fetch_task, return_exceptions=True)
                raise

            # Handle possible errors in buffer task
            if buffer_task.done():
                fetch_task.cancel()
                with suppress(Exception):   # if stream failed, fetch exceptions are not relevant
                    await fetch_task
                raise buffer_task.exception()

            # Stop buffering and retrieve results
            buffer_task.cancel()
            buffered_events = await buffer_task

            # Merge buffered events to snapshot and process the result
            events, last_update = fetch_task.result()
            events.extend(event for event in buffered_events if event.id > last_update)
            self._process(events)
            last_update = events[-1].id

            # Startup sequence complete, let enable-awaiting tasks resume
            ready.set()
            del ready

            # Past that point, exceptions will not be caught, switch to on_error callback
            try:
                while True:
                    data = await self._receive(ws)
                    events = [event for event in self._decode(data) if event.id > last_update]
                    if events:
                        self._process(events)
                        last_update = events[-1].id
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                self.on_error(self, exc, sys.exc_info())
        finally:
            await ws.close()

    async def _buffer_events(self, ws):
        event_buffer = []
        try:
            while True:
                data = await self._receive(ws)
                event_buffer.extend(self._decode(data))
        except asyncio.CancelledError:
            return event_buffer

    async def _fetch_snapshot(self):
        ''' Fetch a full snapshot of order book depth from REST endpoint.

        :return: 2-tuple with update events diffing from an empty order book, and
                 the index of most recent update taken into account in the snapshot.
        :rtype: list(OrderUpdate), int
        '''

        url = DEPTH_URL.format(symbol=self.symbol.upper())
        try:
            async with self._session.get(url) as response:
                snapshot = await response.json()
        except aiohttp.ClientError as exc:
            raise FeedConnectionError(str(exc)) from exc

        if 'code' in snapshot:
            err_msg = snapshot.get('msg', 'unknown error returned by remote server')
            raise FeedRemoteError(err_msg, code=snapshot['code'])

        try:
            events, last_update = [], int(snapshot['lastUpdateId'])
            events.extend(OrderUpdate(id=last_update, timestamp=None, type='buy',
                                        amount=Decimal(item[1]), price=Decimal(item[0]))
                            for item in snapshot['bids'])
            events.extend(OrderUpdate(id=last_update, timestamp=None, type='sell',
                                        amount=Decimal(item[1]), price=Decimal(item[0]))
                            for item in snapshot['asks'])
        except (KeyError, DecimalException) as exc:
            raise FeedPayloadError('invalid order book snapshot') from exc

        return events, last_update

    def _decode(self, data):
        try:
            id_counter = itertools.count(data['U'])
            bids = (OrderUpdate(id=next(id_counter), timestamp=int(data['E']),
                                type='buy', amount=Decimal(item[1]), price=Decimal(item[0]))
                    for item in data['b'])
            asks = (OrderUpdate(id=next(id_counter), timestamp=int(data['E']),
                                type='sell', amount=Decimal(item[1]), price=Decimal(item[0]))
                    for item in data['a'])
            return list(itertools.chain(bids, asks))
        except (KeyError, DecimalException) as exc:
            raise FeedPayloadError('invalid order book update') from exc

    def _process(self, events):
        self.on_update(self, data=events)
