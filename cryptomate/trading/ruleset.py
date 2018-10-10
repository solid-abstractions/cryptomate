

class RuleSet:
    ''' Relevant trading rules for an :class:`~cryptomate.trading.account.Account` and market.

    :ivar str ~RuleSet.symbol: Market symbol. Actual meaning depends on platform.
    :ivar tuple assets: A 2-tuple of asset names (primary then secondary asset).
    :ivar ~decimal.Decimal lot_size: Granularity of orders, in primary asset amounts.
    :ivar ~decimal.Decimal min_lot: Minimum amount of an order, in primary asset.
    :ivar ~decimal.Decimal max_lot: Maximum amount of an order, in primary asset.
    :ivar ~decimal.Decimal tick_size: Granularity of price, in secondary asset value.
    :ivar ~decimal.Decimal min_price: Minimum order price, in secondary asset value.
    :ivar ~decimal.Decimal max_price: Maximum order price, in secondary asset value.
    :ivar price_limit: Maximum daily variation of the price, in secondary asset value.
    :vartype price_limit: ~decimal.Decimal or None.
    :ivar leverage: Maximum allowed leverage, if the market supports margin trading, `None` if
                    it does not.
    :vartype leverage: ~decimal.Decimal or None.
    :ivar int orders_rate_limit: Maximum orders that can be added per second. Hard limit.
    :ivar int orders_rate_target: Maximum orders that can be added per second. Soft limit.
    :ivar dict options: Optional, platform-dependent features.
    '''
    pass
