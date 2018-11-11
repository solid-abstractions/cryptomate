import aiohttp
import asyncio
import collections
import pytest
from decimal import Decimal
from functools import partial
from unittest import mock
from tests.util.aiohttp import LocalServer, ManualResponseServer, route, redirector
from cryptomate.market.data import OrderUpdate, Tick
from cryptomate.market.feed import FeedEvent, FeedConnectionError, FeedPayloadError
from cryptomate.market.feed.binance import BinanceFeed

TIMEOUT=1

# ============================================================================
# Fixtures

@pytest.fixture
def feed(redirector):
    class TestBinanceFeed(BinanceFeed):
        def __init__(self, *, session):
            self.callback_called = asyncio.Event()
            self.on_error_called = asyncio.Event()
            callback = mock.Mock(
                side_effect=lambda *args, **kwargs: self.callback_called.set()
            )
            on_error = mock.Mock(
                side_effect=lambda *args, **kwargs: self.on_error_called.set()
            )
            super().__init__(
                callback=mock.Mock(side_effect=lambda *args, **kwargs: self.callback_called.set()),
                on_error=mock.Mock(side_effect=lambda *args, **kwargs: self.on_error_called.set()),
                session=session
            )
    return TestBinanceFeed(session=redirector.session)


class BinanceTestWSServer(LocalServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received = asyncio.Queue()
        self.ws = {}

    @route('/ws/{stream}')
    async def trade(self, request):
        stream = request.match_info['stream']
        ws = self.ws[stream] = await self.make_websocket(request)
        async for msg in ws:
            self.received.put_nowait((stream, msg.json()))
        return ws


# ============================================================================
# Tick stream tests

@pytest.mark.asyncio
async def test_tick_events(redirector, ssl_certificate, feed):
    async with BinanceTestWSServer(certificate=ssl_certificate) as server:
        redirector.add_server('stream.binance.com', 9443, server.port)

        # Connect to tick stream
        await feed.enable('btcusdt', FeedEvent.TICK)
        assert 'btcusdt@trade' in server.ws
        assert server.received.empty()
        assert not feed.callback.called
        assert not feed.on_error.called

        # Receive tick event
        await server.ws['btcusdt@trade'].send_str(
            '{"e": "trade", "E": 123456789, "s": "BTCUSDT", "t": 12345, '
            '"p": "10.000", "q": "100", "b": 88, "a": 50, '
            '"T": 123456785, "m": true, "M": true}'
        )
        await asyncio.wait_for(feed.callback_called.wait(), TIMEOUT)

        assert server.received.empty()
        assert feed.callback.call_count == 1
        assert feed.callback.call_args == (
            (feed, 'btcusdt', FeedEvent.TICK),
            {'data': Tick(id=12345, timestamp=123456789,
                          type='sell', amount=Decimal('100'), price=Decimal('10.000'))}
        )
        assert not feed.on_error.called

        # Receive another tick event
        await server.ws['btcusdt@trade'].send_str(
            '{"e": "trade", "E": 123456790, "s": "BTCUSDT", "t": 12346, '
            '"p": "9.980", "q": "100", "b": 88, "a": 50, '
            '"T": 123456788, "m": false, "M": true}'
        )
        await asyncio.wait_for(feed.callback_called.wait(), TIMEOUT)

        assert server.received.empty()
        assert feed.callback.call_count == 2
        assert feed.callback.call_args == (
            (feed, 'btcusdt', FeedEvent.TICK),
            {'data': Tick(id=12346, timestamp=123456790,
                          type='buy', amount=Decimal('100'), price=Decimal('9.980'))}
        )
        assert not feed.on_error.called

        # Disconnect from tick stream
        await feed.disable('btcusdt', FeedEvent.TICK)

        assert server.received.empty()
        assert feed.callback.call_count == 2
        assert server.ws['btcusdt@trade'].closed # graceful shutdown guarantees this


@pytest.mark.asyncio
async def test_tick_server_unreachable(feed):
    ''' Attempt connection, but server cannot be resolved '''

    with pytest.raises(FeedConnectionError):
        await feed.enable('btcusdt', FeedEvent.TICK)
    assert not feed.callback.called
    assert not feed.on_error.called


@pytest.mark.asyncio
async def test_tick_reply_invalid(redirector, ssl_certificate, feed):
    ''' Attempt connection, but server gives invalid reply '''

    async with LocalServer(certificate=ssl_certificate) as server:
        redirector.add_server('stream.binance.com', 9443, server.port)
        with pytest.raises(FeedConnectionError):
            await feed.enable('btcusdt', FeedEvent.TICK)


@pytest.mark.asyncio
async def test_tick_payload_invalid(redirector, ssl_certificate, feed):
    ''' Connection is successful but server sends nonsensical data '''
    async with BinanceTestWSServer(certificate=ssl_certificate) as server:
        redirector.add_server('stream.binance.com', 9443, server.port)

        await feed.enable('btcusdt', FeedEvent.TICK)
        await server.ws['btcusdt@trade'].send_str('invalid')
        await asyncio.wait_for(feed.on_error_called.wait(), TIMEOUT)

        assert feed.on_error.call_count == 1
        assert feed.on_error.call_args[0] == (feed, 'btcusdt', FeedEvent.TICK)
        assert isinstance(feed.on_error.call_args[1]['exc'], FeedPayloadError)
        assert isinstance(feed.on_error.call_args[1]['msg'], str)
        assert feed.on_error.call_args[1]['retry'] == 0

        # Server sends invalid JSON frame

        await feed.enable('btcusdt', FeedEvent.TICK)
        await server.ws['btcusdt@trade'].send_str('{"foo": 42, "bar": "baz"}')
        await asyncio.wait_for(feed.on_error_called.wait(), TIMEOUT)

        assert feed.on_error.call_count == 2
        assert feed.on_error.call_args[0] == (feed, 'btcusdt', FeedEvent.TICK)
        assert isinstance(feed.on_error.call_args[1]['exc'], FeedPayloadError)
        assert isinstance(feed.on_error.call_args[1]['msg'], str)
        assert feed.on_error.call_args[1]['retry'] == 0


@pytest.mark.asyncio
async def test_tick_disconnect(redirector, ssl_certificate, feed):
    ''' Connection to server is lost, or closed at server's initiative '''
    async with BinanceTestWSServer(certificate=ssl_certificate) as server:
        redirector.add_server('stream.binance.com', 9443, server.port)

        # Server disconnects
        feed.on_error_called.clear()
        await feed.enable('btcusdt', FeedEvent.TICK)

        await server.ws['btcusdt@trade'].close()
        await asyncio.wait_for(feed.on_error_called.wait(), TIMEOUT)

        assert feed.on_error.call_count == 1
        assert feed.on_error.call_args[0] == (feed, 'btcusdt', FeedEvent.TICK)
        assert isinstance(feed.on_error.call_args[1]['exc'], FeedConnectionError)

# ============================================================================
# OrderBook stream tests

@pytest.mark.asyncio
async def test_orderbook_events(redirector, ssl_certificate, feed):
    async with ManualResponseServer(certificate=ssl_certificate) as server:
        async with BinanceTestWSServer(certificate=ssl_certificate) as wsserver:
            redirector.add_server('www.binance.com', 443, server.port)
            redirector.add_server('stream.binance.com', 9443, wsserver.port)

            # Connect to orderbook stream
            start_task = asyncio.ensure_future(feed.enable('btcusdt', FeedEvent.ORDERBOOK))
            request = await server.receive_request(timeout=TIMEOUT)
            assert request.path_qs == '/api/v1/depth?symbol=BTCUSDT&limit=1000'
            server.send_response(
                text='{"lastUpdateId": 1027024, '
                     '"bids": [["4.00000000", "431.00000000", []]], '
                     '"asks": [["4.00000200", "12.00000000", []]] }',
                content_type='application/json'
            )

            await asyncio.wait_for(start_task, TIMEOUT)
            assert 'btcusdt@depth' in wsserver.ws
            assert wsserver.received.empty()
            assert feed.callback.call_count == 1
            assert feed.callback.call_args[0] == (feed, 'btcusdt', FeedEvent.ORDERBOOK)
            assert feed.callback.call_args[1] == {
                'data': [OrderUpdate(id=1027024, timestamp=None, type='buy',
                                     amount=Decimal('431.00000000'), price=Decimal('4.00000000')),
                         OrderUpdate(id=1027024, timestamp=None, type='sell',
                                     amount=Decimal('12.00000000'), price=Decimal('4.00000200'))]
            }
            assert not feed.on_error.called

            # Send some updates
            feed.callback_called.clear()
            await wsserver.ws['btcusdt@depth'].send_str(
                '{ "e": "depthUpdate", "E": 123456789, "s": "BTCUSDT", "U": 1027025, "u": 1027026, '
                '"b": [[ "0.0024", "10", []]], "a": [[ "0.0026", "100", []]]}'
            )
            await asyncio.wait_for(feed.callback_called.wait(), TIMEOUT)
            assert feed.callback.call_count == 2
            assert feed.callback.call_args[0] == (feed, 'btcusdt', FeedEvent.ORDERBOOK)
            assert feed.callback.call_args[1] == {
                'data': [OrderUpdate(id=1027025, timestamp=123456789, type='buy',
                                     amount=Decimal('10'), price=Decimal('0.0024')),
                         OrderUpdate(id=1027026, timestamp=123456789, type='sell',
                                     amount=Decimal('100'), price=Decimal('0.0026'))]
            }
            assert not feed.on_error.called

            # Close feed
            await asyncio.wait_for(feed.disable('btcusdt', FeedEvent.ORDERBOOK), TIMEOUT)
            assert wsserver.ws['btcusdt@depth'].closed # graceful shutdown guarantees this


@pytest.mark.asyncio
async def test_orderbook_buffering(redirector, ssl_certificate, feed):
    async with ManualResponseServer(certificate=ssl_certificate) as server:
        async with BinanceTestWSServer(certificate=ssl_certificate) as wsserver:
            redirector.add_server('www.binance.com', 443, server.port)
            redirector.add_server('stream.binance.com', 9443, wsserver.port)

            # Connect to orderbook stream
            start_task = asyncio.ensure_future(feed.enable('btcusdt', FeedEvent.ORDERBOOK))
            request = await server.receive_request(timeout=TIMEOUT)
            assert request.path_qs == '/api/v1/depth?symbol=BTCUSDT&limit=1000'

            # Snapshot update was requested, delay answer and send events in the meantime
            await wsserver.ws['btcusdt@depth'].send_str(
                '{ "e": "depthUpdate", "E": 123456789, "s": "BTCUSDT", "U": 98, "u": 99, '
                '"b": [[ "0.0024", "10", []]], "a": [[ "0.0026", "100", []]]}'
            )
            await wsserver.ws['btcusdt@depth'].send_str(
                '{ "e": "depthUpdate", "E": 123456789, "s": "BTCUSDT", "U": 100, "u": 101, '
                '"b": [[ "0.0023", "20", []]], "a": [[ "0.0027", "200", []]]}'
            )
            await wsserver.ws['btcusdt@depth'].send_str(
                '{ "e": "depthUpdate", "E": 123456789, "s": "BTCUSDT", "U": 102, "u": 103, '
                '"b": [[ "0.0022", "30", []]], "a": [[ "0.0028", "300", []]]}'
            )
            await asyncio.sleep(0)
            server.send_response(
                text='{"lastUpdateId": 101, '
                     '"bids": [["4.00000000", "431.00000000", []]], '
                     '"asks": [["4.00000200", "12.00000000", []]]}',
                content_type='application/json',
            )

            # Complete connection and check result
            await asyncio.wait_for(start_task, TIMEOUT)
            assert wsserver.received.empty()
            assert feed.callback.call_count == 1
            assert feed.callback.call_args[0] == (feed, 'btcusdt', FeedEvent.ORDERBOOK)
            assert feed.callback.call_args[1] == {
                'data': [OrderUpdate(id=101, timestamp=None, type='buy',
                                     amount=Decimal('431.00000000'), price=Decimal('4.00000000')),
                         OrderUpdate(id=101, timestamp=None, type='sell',
                                     amount=Decimal('12.00000000'), price=Decimal('4.00000200')),
                         OrderUpdate(id=102, timestamp=123456789, type='buy',
                                     amount=Decimal('30'), price=Decimal('0.0022')),
                         OrderUpdate(id=103, timestamp=123456789, type='sell',
                                     amount=Decimal('300'), price=Decimal('0.0028'))]
            }
            assert not feed.on_error.called

            # Send two additional updates, one old and one new. Only new must pass.
            feed.callback_called.clear()
            await wsserver.ws['btcusdt@depth'].send_str(
                '{ "e": "depthUpdate", "E": 123456789, "s": "BTCUSDT", "U": 101, "u": 102, '
                '"b": [[ "0.0022", "30", []]], "a": [[ "0.0028", "300", []]]}'
            )
            await wsserver.ws['btcusdt@depth'].send_str(
                '{ "e": "depthUpdate", "E": 123456789, "s": "BTCUSDT", "U": 104, "u": 105, '
                '"b": [[ "0.0021", "0", []]], "a": [[ "0.0029", "0", []]]}'
            )
            await asyncio.wait_for(feed.callback_called.wait(), TIMEOUT)
            assert wsserver.received.empty()
            assert feed.callback.call_count == 2
            assert feed.callback.call_args[0] == (feed, 'btcusdt', FeedEvent.ORDERBOOK)
            assert feed.callback.call_args[1] == {
                'data': [OrderUpdate(id=104, timestamp=123456789, type='buy',
                                     amount=Decimal('0'), price=Decimal('0.0021')),
                         OrderUpdate(id=105, timestamp=123456789, type='sell',
                                     amount=Decimal('0'), price=Decimal('0.0029'))]
            }
            assert not feed.on_error.called

            # Close feed
            await asyncio.wait_for(feed.disable('btcusdt', FeedEvent.ORDERBOOK), TIMEOUT)
            assert wsserver.ws['btcusdt@depth'].closed # graceful shutdown guarantees this


@pytest.mark.asyncio
async def test_orderbook_enable_cancellation(redirector, ssl_certificate, feed):
    async with ManualResponseServer(certificate=ssl_certificate) as server:
        async with BinanceTestWSServer(certificate=ssl_certificate) as wsserver:
            redirector.add_server('www.binance.com', 443, server.port)
            redirector.add_server('stream.binance.com', 9443, wsserver.port)

            # Send invalid JSON frame during startup sequence
            start_task = asyncio.ensure_future(feed.enable('btcusdt', FeedEvent.ORDERBOOK))
            request = await server.receive_request(timeout=TIMEOUT)

            start_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(start_task, TIMEOUT)

            assert not feed.callback.called
            assert not feed.on_error.called
            assert wsserver.ws['btcusdt@depth'].closed # graceful shutdown guarantees this


@pytest.mark.asyncio
async def test_orderbook_payload_invalid_during_startup(redirector, ssl_certificate, feed):
    async with ManualResponseServer(certificate=ssl_certificate) as server:
        async with BinanceTestWSServer(certificate=ssl_certificate) as wsserver:
            redirector.add_server('www.binance.com', 443, server.port)
            redirector.add_server('stream.binance.com', 9443, wsserver.port)

            # Send invalid JSON frame during startup sequence
            start_task = asyncio.ensure_future(feed.enable('btcusdt', FeedEvent.ORDERBOOK))
            request = await server.receive_request(timeout=TIMEOUT)

            await wsserver.ws['btcusdt@depth'].send_str('{"foo": 42, "bar": "baz"}')
            with pytest.raises(FeedPayloadError):
                await asyncio.wait_for(start_task, TIMEOUT)
            assert feed.callback.call_count == 0
            assert feed.on_error.call_count == 0
            assert wsserver.ws['btcusdt@depth'].closed


@pytest.mark.asyncio
async def test_orderbook_snapshot_invalid(redirector, ssl_certificate, feed):
    async with ManualResponseServer(certificate=ssl_certificate) as server:
        async with BinanceTestWSServer(certificate=ssl_certificate) as wsserver:
            redirector.add_server('www.binance.com', 443, server.port)
            redirector.add_server('stream.binance.com', 9443, wsserver.port)

            # Send invalid order book snapshot
            start_task = asyncio.ensure_future(feed.enable('btcusdt', FeedEvent.ORDERBOOK))
            request = await server.receive_request(timeout=TIMEOUT)
            server.send_response(text='{"foo": 42, "bar": "baz"}', content_type='application/json')

            with pytest.raises(FeedPayloadError):
                await asyncio.wait_for(start_task, TIMEOUT)
            assert feed.callback.call_count == 0
            assert feed.on_error.call_count == 0
            assert wsserver.ws['btcusdt@depth'].closed


@pytest.mark.asyncio
async def test_orderbook_payload_invalid(redirector, ssl_certificate, feed):
    async with ManualResponseServer(certificate=ssl_certificate) as server:
        async with BinanceTestWSServer(certificate=ssl_certificate) as wsserver:
            redirector.add_server('www.binance.com', 443, server.port)
            redirector.add_server('stream.binance.com', 9443, wsserver.port)

            # Connect
            start_task = asyncio.ensure_future(feed.enable('btcusdt', FeedEvent.ORDERBOOK))
            request = await server.receive_request(timeout=TIMEOUT)
            server.send_response(
                text='{"lastUpdateId": 101, '
                     '"bids": [["4.00000000", "431.00000000", []]], '
                     '"asks": [["4.00000200", "12.00000000", []]]}',
                content_type='application/json',
            )
            await asyncio.wait_for(start_task, TIMEOUT)

            # Send invalid JSON data
            await wsserver.ws['btcusdt@depth'].send_str('{"foo": 42, "bar": "baz"}')

            await asyncio.wait_for(feed.on_error_called.wait(), TIMEOUT)
            assert feed.callback.call_count == 1
            assert feed.on_error.call_count == 1
            assert feed.on_error.call_args[0] == (feed, 'btcusdt', FeedEvent.ORDERBOOK)
            assert isinstance(feed.on_error.call_args[1]['exc'], FeedPayloadError)


@pytest.mark.asyncio
async def test_orderbook_disconnect(redirector, ssl_certificate, feed):
    async with ManualResponseServer(certificate=ssl_certificate) as server:
        async with BinanceTestWSServer(certificate=ssl_certificate) as wsserver:
            redirector.add_server('www.binance.com', 443, server.port)
            redirector.add_server('stream.binance.com', 9443, wsserver.port)

            # Connect
            start_task = asyncio.ensure_future(feed.enable('btcusdt', FeedEvent.ORDERBOOK))
            request = await server.receive_request(timeout=TIMEOUT)
            server.send_response(
                text='{"lastUpdateId": 101, '
                     '"bids": [["4.00000000", "431.00000000", []]], '
                     '"asks": [["4.00000200", "12.00000000", []]]}',
                content_type='application/json',
            )
            await asyncio.wait_for(start_task, TIMEOUT)

            assert feed.callback.call_count == 1
            assert feed.on_error.call_count == 0

            # Server disconnects
            await wsserver.ws['btcusdt@depth'].close()
            await asyncio.wait_for(feed.on_error_called.wait(), TIMEOUT)
            assert feed.on_error.call_count == 1
            assert feed.on_error.call_args[0] == (feed, 'btcusdt', FeedEvent.ORDERBOOK)
            assert isinstance(feed.on_error.call_args[1]['exc'], FeedConnectionError)
