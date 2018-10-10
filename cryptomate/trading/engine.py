

class Engine:
    ''' Main port entry point.
    '''

    async def open(self, description):
        ''' Open a trading account.

        :param description: identification and credentials of account.
        :paramtype description: ~cryptomate.trading.data.AccountDescription
        :return: an :class:`~cryptomate.trading.account.Account` instance.
        '''
        raise NotImplementedError
