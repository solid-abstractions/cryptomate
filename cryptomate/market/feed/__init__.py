import asyncio
from cryptomate.market.feed.base import Feed, FeedEvent
from cryptomate.market.feed.factory import Factory, default_factory, register

class FeedError(Exception):             ''' Base class for all errors raised by feeds '''
class FeedConnectionError(FeedError):   ''' Transport-level error (in connection to feed) '''
class FeedPayloadError(FeedError):      ''' Data received from feed could not be understood '''
class FeedRateLimitError(FeedError):    ''' Rate limit exceeded in unrecoverable way '''
class FeedRemoteError(FeedError):       ''' Generic error condition reported by feed provider '''
class FeedTimeoutError(FeedError, asyncio.TimeoutError):
    ''' Operation exceeded allocated time '''

__all__ = (
    'Feed', 'FeedEvent',
    'Factory', 'default_factory', 'register',
)
