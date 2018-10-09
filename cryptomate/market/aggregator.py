

class Aggregator:
    ''' Aggregated candle data over a configurable time period.

    :ivar int period: Aggregation timeframe in seconds.
    '''

    def __len__(self):
        ''' Number of candles currently buffered. '''
        raise NotImplementedError

    def __getitem__(self, idx):
        ''' Read candle.

        :param int idx: Position of candle, starting from 0 for current candle, and incrementing
                        for past candles. Negative numbers count from the end.
        :return: a :class:`~cryptomate.market.data.Candle` instance.
        '''
        raise NotImplementedError
