from decimal import Decimal, DecimalException
from cryptomate.market.data import Tick
from cryptomate.market.feed import FeedEvent, FeedPayloadError
from cryptomate.market.feed.binance.stream import Stream


class TickStream(Stream):
    ''' Worker that receives events from a market tick stream '''

    event = FeedEvent.TICK
    __slots__ = ('symbol', 'on_tick')

    def __init__(self, symbol, *, on_tick, **kwargs):
        super().__init__(**kwargs)
        self.symbol = symbol
        self.on_tick = on_tick

    @property
    def _name(self):
        return f'{self.symbol}@trade'

    def _decode(self, data):
        try:
            return Tick(
                id=int(data['t']),
                timestamp=int(data['E']),
                type='sell' if data['m'] else 'buy',
                amount=Decimal(data['q']),
                price=Decimal(data['p']),
            )
        except (KeyError, ValueError, DecimalException) as exc:
            raise FeedPayloadError(str(exc)) from exc

    def _process(self, event):
        self.on_tick(self, data=event)
