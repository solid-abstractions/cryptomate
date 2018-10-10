from collections import namedtuple


AccountDescription = namedtuple('AccountDescription', 'name data', module=__name__)
AccountDescription.__doc__ = ''' Identifies an account on an exchange

:param str name: Platform name.
:param str data: Account identifiers and credentials. Actual format depends on platform.
'''

Trade = namedtuple('Trade', 'id timestamp symbol side amount price fee', module=__name__)
Trade.__doc__ = ''' A single trade resulting from an order.

:param str id: Trade identifier.
:param int timestamp: Number of seconds between the Epoch and the time the trade happened at.
:param str symbol: Market symbol. Actual meaning depends on platform.
:param str side: ``buy`` or ``sell``.
:param ~decimal.Decimal amount: Order volume in traded asset.
:param ~decimal.Decimal price: Order price in secondary asset.
:param ~decimal.Decimal fee: Price paid to exchange in secondary asset.
'''
