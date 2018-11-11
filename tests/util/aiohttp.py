import aiohttp
import aiohttp.test_utils
import aiohttp.web
import asyncio
import collections
import pytest
import socket
import ssl
import weakref


# ----------------------------------------------------------------------------

RedirectContext = collections.namedtuple('RedirectContext', 'add_server session')

@pytest.fixture
async def redirector(ssl_certificate):
    ''' An HTTP ClientSession fixture that redirects requests to local test servers

        Returned session has a `add_server(host, port, local_port)` member function
        to add test servers to the list of redirections.
    '''

    resolver = FakeResolver()
    ssl_context = ssl.SSLContext()
    ssl_context.verify_mode = ssl.VerifyMode.CERT_REQUIRED
    ssl_certificate.allow_verify(ssl_context)
    connector = aiohttp.TCPConnector(resolver=resolver, ssl=ssl_context, use_dns_cache=False)

    async with aiohttp.ClientSession(connector=connector) as session:
        yield RedirectContext(add_server=resolver.add, session=session)


class FakeResolver(object):
    ''' aiohttp resolver that hijacks a set of uris

    :param servers: a mapping of remote host:port to redirect to local servers.
    :type servers: dict(tuple(str, int), int)
    '''
    __slots__ = ('_servers',)

    def __init__(self, servers=None):
        self._servers = servers or {}

    def add(self, host, port, target):
        ''' Add an entry to the resolver

        :param str host: hostname that should be redirected to the test server.
        :param int port: target port that should be redirected to the test server.
        :param int target: port the local test server runs on.
        '''
        self._servers[host, port] = target

    async def resolve(self, host, port=0, family=socket.AF_INET):
        ''' Resolve a host:port pair into a connectable address

        :param str host: hostname to resolve.
        :param int port: which port to connect to.
        :param int family: socket family. Only `AF_INET` supported.
        :return: list of resolved addresses. Always one entry.
        :raise OSError: requested hostname:port is not known to the resolver.
        '''
        try:
            fake_port = self._servers[host, port]
        except KeyError:
            raise OSError('Fake DNS lookup failed: no fake server known for %s' % host)
        return [{
            'hostname': host,
            'host': '127.0.0.1',
            'port': fake_port,
            'family': socket.AF_INET,
            'proto': 0,
            'flags': socket.AI_NUMERICHOST,
        }]

# ----------------------------------------------------------------------------


def route(path, method='get'):
    ''' decorate a LocalServer method so it gets routed automatically '''
    def decorator(fn):
        fn.path = path
        fn.method = method
        return fn
    return decorator


class LocalServer(object):
    ''' A simple http server usable as a context manager, to kick all connections easily.

    :param certificate: a certificate fixture, or :const:`None` to disable SSL.
    :type certificate: tests.util.certificate.TemporaryCertificate or None
    :param loop: event loop to associate the server with. :const:`None` to use default loop.
    :type loop: asyncio.AbstractEventLoop or None

    :ivar app: wrapped application instance.
    :vartype app: aiohttp.web.Application
    :ivar int port: local port number the server runs on.
    '''

    __slots__ = ('app', 'port', '_certificate', '_runner', '_websockets')

    def __init__(self, *, certificate=None, loop=None):
        self.app = aiohttp.web.Application(loop=loop)
        self._certificate = certificate
        self._websockets = weakref.WeakSet()

        for key in dir(self):
            value = getattr(self, key, None)
            if callable(value) and hasattr(value, 'path') and hasattr(value, 'method'):
                self.app.router.add_route(value.method, value.path, value)

    async def __aenter__(self):
        ''' On context entry, start the web server '''
        self.port = aiohttp.test_utils.unused_port()
        self._runner = aiohttp.web.AppRunner(self.app)
        await self._runner.setup()

        if self._certificate:
            ssl_context = ssl.SSLContext()
            self._certificate.load_into(ssl_context)
        else:
            ssl_context = None

        site = aiohttp.web.TCPSite(self._runner, '127.0.0.1', self.port, ssl_context=ssl_context)
        await site.start()
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        ''' On context exit, kill websockets and shut the web server down '''
        if self._websockets:
            await asyncio.wait([ws.close() for ws in self._websockets])
        await self._runner.cleanup()

    async def make_websocket(self, request):
        ''' Switch request to websocket protocol.

        The websocket is marked to be forcibly closed on server shutdown.

        :param request: request to upgrade to websocket protocol.
        :type request: aiohttp.web.BaseRequest
        :rtype: aiohttp.web.WebSocketResponse
        '''
        ws = aiohttp.web.WebSocketResponse()
        await ws.prepare(request)
        self._websockets.add(ws)
        return ws


class ManualResponseServer(LocalServer):
    ''' Local server that relies on test case to supply responses and control timing '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = asyncio.Queue()
        self.response = asyncio.Queue()
        self._requests = []

    async def __aexit__(self, exc_type, exc, traceback):
        for task in self._requests:
            task.cancel()
        await super().__aexit__(exc_type, exc, traceback)

    @route('/{path:.*}')
    async def _request(self, request):
        task = asyncio.Task.current_task()
        self.request.put_nowait(request)
        self._requests.append(task)
        response = await self.response.get()
        self._requests.remove(task)
        return response

    async def receive_request(self, *, timeout=None):
        ''' Wait until the test server receives a request

        :param float timeout: Bail out after that many seconds.
        :return: received request, not yet serviced.
        :rtype: aiohttp.web.BaseRequest
        :see: :meth:`send_response`
        '''
        return await asyncio.wait_for(self.request.get(), timeout=timeout)

    def send_response(self, *args, **kwargs):
        ''' Reply to a received request.

        :note: must be used in same order received were received.
        :param args: forwarded to :class:`aiohttp.web.Response`.
        :param kwargs: forwarded to :class:`aiohttp.web.Response`.
        '''
        self.response.put_nowait(aiohttp.web.Response(*args, **kwargs))
