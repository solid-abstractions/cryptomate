from abc import ABC, abstractmethod


class Account(ABC):
    ''' A valid, opened account on a trading platform.

    :ivar callback: the callable that is invoked on every event on the account.
    :vartype callback: ~collections.abc.Callable or None
    :ivar orders: all orders currently open or partially filled on this account.
    :vartype orders: ~collections.abc.Container(Order)
    :ivar balance: current balance in each asset.
    :vartype balance: ~collections.abc.Mapping(str, ~decimal.Decimal)
    :ivar equity: current counter-value of the account.
    :ivar ~decimal.Decimal margin_balance: available margin for trading.
    :ivar ~decimal.Decimal used_margin: margin currently locked as collateral.
    :ivar float margin_level: :attr:`equity` to :attr:`used_margin` ratio.
    '''

    @abstractmethod
    def close(self):
        ''' Release the account and associated resources '''
        raise NotImplementedError

    @abstractmethod
    async def add_order(self, order, options=None):
        ''' Send a new order to the exchange.

        :param Order order: Full description of the order.
        :param options: Additional options (such as post-only). Platform-dependent.
        :paramtype options: dict or None.
        '''
        raise NotImplementedError

    @abstractmethod
    async def cancel_order(self, order_id):
        ''' Cancel the order with given id. '''
        raise NotImplementedError

    @abstractmethod
    def get_rules(self, symbol):
        ''' Get the trading rules for a market.

        :param str symbol: Market symbol. Actual meaning depends on platform.
        :rtype: ~cryptomate.trading.ruleset.RuleSet
        '''
        raise NotImplementedError


class Order:
    ''' Buy/sell intent, currently active on the market.

    :ivar timestamp: Number of seconds between the Epoch and order creation.
    :ivar ~Order.type: ``limit`` or ``market``.
    :ivar side: ``buy`` or ``sell``.
    :ivar expiration: Number of seconds between the Epoch and order expiration.
    :ivar ~decimal.Decimal amount: Order volume in traded asset.
    :ivar price: Order price in secondary asset. `None` for market orders.
    :vartype price: ~decimal.Decimal or None.
    :ivar leverage: Level of leveraging of using margin trading, or `None` if not.
    :vartype leverage: ~decimal.Decimal or None.
    :ivar trades: List of trades generated by this order.
    :vartype trades: ~collections.abc.Sequence(~cryptomate.trading.data.Trade)
    :ivar ~decimal.Decimal executed:
    '''
    __slots__ = ('timestamp', 'type', 'side', 'expiration', 'amount',
                 'price', 'leverage', 'trades', 'executed')
