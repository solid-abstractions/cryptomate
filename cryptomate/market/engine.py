

class Engine:
    ''' Main port entry point, manageds feeds according to subscriptions.
    '''
    async def subscribe_orderbook(self, description, callback):
        ''' Subscribe to order book updates

        :param ~cryptomate.market.data.FeedDescription description: identification of feed.
        :param callback: a callable that will be invoked on every event.
        :return: a :class:`OrderBookSubscription` instance.
        '''
        raise NotImplementedError

    async def subscribe_ticks(self, description, callback):
        ''' Subscribe to a market feed

        :param ~cryptomate.market.data.FeedDescription description: identification of feed.
        :param callback: a callable that will be invoked on every event.
        :return: a :class:`TickSubscription` instance.
        '''
        raise NotImplementedError


class OrderBookSubscription:
    ''' An active subscription to a market order book

    :ivar order_book: an :class:`~cryptomate.market.orderbook.OrderBook` instance with buffered
                      data for the feed.
    '''
    def close(self):
        ''' Cancel the subscription '''
        raise NotImplementedError

    def __enter__(self):
        ''' Context manager interface

        Enables using the subscription as a context manager, for instance::

            with await engine.subscribe_orderbook(description, callback) as subscription:
                do_something()
        '''
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()


class TickSubscription:
    ''' An active subscription to a market feed

    :ivar data: an Aggregator instance with buffered data for the feed. `None` if the subscription
                is tick-based.
    :vartype data: ~cryptomate.market.aggregator.Aggregator or None
    '''

    def close(self):
        ''' Cancel the subscription '''
        raise NotImplementedError

    def __enter__(self):
        ''' Context manager interface

        Enables using the subscription as a context manager, for instance::

            with await engine.subscribe(description, callback) as subscription:
                do_something()
        '''
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
