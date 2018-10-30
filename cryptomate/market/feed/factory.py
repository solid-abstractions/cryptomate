from cryptomate.market import FeedDescription
from cryptomate.market.feed import Feed


class Factory:
    ''' Abstract out details for selecting a feed class and instantiating it.
    '''
    __slots__ = ('_classes',)

    def __init__(self, *, classes=None):
        self._classes = classes or {}

    def register(self, feed):
        ''' Register a feed class with the factory

        :param feed: a subclass of :class:`~cryptomate.market.feed.base.Feed`.
        :return: ``feed``, so this method can be used as a decorator.
        '''
        if not issubclass(feed, Feed):
            raise TypeError('attempting to register invalid class %s' % feed.__name__)
        self._classes[feed.name] = feed
        return feed

    def create(self, description, *, callback, on_error):
        ''' Instantiate a feed from a description

        :param description: describes the feed to instantiate.
        :paramtype description: ~cryptomate.market.FeedDescription
        :param callable callback: a function invoked on every event.
                                  Has form ``callback(feed, symbol, event, data)``
        :param callable on_error: invoked when an enabled event stream gets an error condition.
                                  Has form ``on_error(feed, symbol, event, exc=None, retry, msg)``
        :return: a feed instance than can handle the described feed.
        :rtype: ~cryptomate.market.feed.base.Feed
        '''
        if not isinstance(description, FeedDescription):
            raise TypeError('description must be a FeedDescription, not %s'
                            % description.__class__.__name__)
        try:
            klass = self._classes[description.name]
        except KeyError:
            raise ValueError('no feed with name %s' % description.name)
        return klass(callback=callback, on_error=on_error)

default_factory = Factory()
register = default_factory.register
