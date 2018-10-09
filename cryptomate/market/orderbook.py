
class OrderBook:
    ''' Instant representation of the order book.

    :ivar buy: Bid side of the order book.
    :vartype buy: ~collections.abc.Mapping(~decimal.Decimal, ~decimal.Decimal)
    :ivar sell: Ask side of the order book.
    :vartype sell: ~collections.abc.Mapping(~decimal.Decimal, ~decimal.Decimal)
    '''

    def update(self, updates):
        ''' Update the data in the order book.

        :var updates: A collection of updates to perform.
        :vartype updates: ~collections.abc.Collection(~cryptomate.market.data.OrderUpdate)
        '''
        raise NotImplementedError
