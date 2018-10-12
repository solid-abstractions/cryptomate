from abc import ABC, abstractmethod


class History(ABC):
    ''' Random-access to past market events. '''

    @abstractmethod
    async def get_reader(self, description):
        ''' Get a reader handle for a market feed description.

        :param ~cryptomate.market.data.FeedDescription description: identification of feed.
        :rtype: Reader
        '''
        raise NotImplementedError

    @abstractmethod
    async def get_writer(self, description):
        ''' Get a writer handle for a market feed description.

        :param ~cryptomate.market.data.FeedDescription description: identification of feed.
        :rtype: Writer
        '''
        raise NotImplementedError


class Reader(ABC):
    ''' A read handle to market history data

    :ivar bool has_candles: whether
    :ivar bool has_ticks:
    :ivar bool has_order_updates:
    :ivar int earliest_timestamp: Number of seconds between the Epoch and the oldest data known.
    :ivar int newest_timestamp: Number of seconds between the Epoch and the most recent data known.
    '''

    @abstractmethod
    async def read_candles(self, start, stop):
        ''' Read candle data.

        :param int start: timestamp of first candle to retrieve (inclusive).
        :param int stop: timestamp of first candle to stop retrieval at (exclusive).
        :rtype: ~collections.abc.Sequence(Candle)
        '''
        raise NotImplementedError

    @abstractmethod
    async def read_ticks(self, start, stop):
        ''' Read tick data.

        :param int start: timestamp of first tick to retrieve (inclusive).
        :param int stop: timestamp of first tick to stop retrieval at (exclusive).
        :rtype: ~collections.abc.Sequence(Tick)
        '''
        raise NotImplementedError

    @abstractmethod
    async def read_order_updates_snapshot(self, timestamp):
        ''' Read the most recent order book snapshot before a point in time.

        :param int timestamp: timestamp of point in time before which the snapshot must
                              has been taken.
        :return: Order book snapshot.
        '''
        raise NotImplementedError

    @abstractmethod
    async def read_order_updates(self, start, stop):
        ''' Read order book updates.

        :param int start: timestamp of first tick to retrieve (inclusive).
        :param int stop: timestamp of first tick to stop retrieval at (exclusive).
        :rtype: ~collections.abc.Sequence(Tick)
        '''
        raise NotImplementedError


class Writer(ABC):
    ''' A write handle to market history data

    :ivar int newest_timestamp: Number of seconds between the Epoch and the most recent data written.
    '''

    @abstractmethod
    async def flush(self):
        ''' Ensures all data written so far has been actually sent to storage. '''
        raise NotImplementedError

    @abstractmethod
    def write_candles(self, candles):
        ''' Write a set of candles to the dataset

        :param candles: Finalized candles to write to the dataset.
        :paramtype candles: ~collections.abc.Sequence(Candle)
        '''
        raise NotImplementedError

    @abstractmethod
    def write_ticks(self, ticks):
        ''' Write a set of ticks to the dataset

        :param ticks: Sequence of ticks to write to the dataset.
        :paramtype ticks: ~collections.abc.Sequence(Tick)
        '''
        raise NotImplementedError

    @abstractmethod
    def write_order_updates(self, updates, *, order_book):
        ''' Write a set of candles to the dataset

        :param updates: Order update events to write to the dataset.
        :paramtype updates: ~collections.abc.Sequence(OrderUpdate)
        :param order_book: Complete view of the order book.
        '''
        raise NotImplementedError
