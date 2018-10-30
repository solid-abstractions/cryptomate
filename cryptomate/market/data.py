from collections import namedtuple

Candle = namedtuple('Candle', 'timestamp open high low close volume', module=__name__)
Candle.__doc__ = ''' An aggregated market data item for a time period.

:param int timestamp: Number of seconds between the Epoch and the start of the period.
:param ~decimal.Decimal open: Price of first transaction that happened within the period.
:param ~decimal.Decimal high: Maximum of price of all transactions within the period.
:param ~decimal.Decimal low: Minimum of price of all transactions within the period.
:param ~decimal.Decimal close: Price of last transaction that happened within the period.
:param ~decimal.Decimal volume: Total transaction volume in traded asset. If 0, then price fields
                       are meaningless and should be None.
'''

FeedDescription = namedtuple('FeedDescription', 'name symbol period', module=__name__)
FeedDescription.__doc__ = ''' Identifies a market on a provider, with aggregation settings.

:param str name: Platform name.
:param str symbol: Market symbol. Actual meaning depends on platform.
:param period: Aggregation timeframe in seconds. `None` for no aggregation (tick-based).
:type period: int or None
'''

OrderUpdate = namedtuple('OrderUpdate', 'id timestamp type amount price', module=__name__)
OrderUpdate.__doc__ = ''' A single order status event on a market's order book.

:param int id: Id of event. Unique for a given market.
:param int timestamp: Number of seconds elapsed from the Epoch to this event.
:param str type: ``buy`` or ``sell``.
:param ~decimal.Decimal amount: Order volume in traded asset.
:param ~decimal.Decimal price: Order price in secondary asset.
'''

Tick = namedtuple('Tick', 'id timestamp type amount price', module=__name__)
Tick.__doc__ = ''' A single transaction on a market.

:param int id: Id of transaction. Unique for a given market.
:param int timestamp: Number of seconds elapsed from the Epoch to that transaction.
:param type: ``buy`` or ``sell``. `None` if the provider does not publish this information.
:type type: str or None
:param ~decimal.Decimal amount: Transaction volume in traded asset.
:param ~decimal.Decimal price: Transaction price in secondary asset.
'''
