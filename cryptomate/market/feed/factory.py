from cryptomate.market.feed import Feed


class Factory:
    def __init__(self):
        self._klasses = {}

    def register(self, name, klass):
        if name in self._klasses:
            raise KeyError('Feed "%s" already registered' % name)
        if not issubclass(klass, Feed):
            raise TypeError('Class "%s" does not inherit Feed' % klass.__name__)
        self._klasses[name] = klass

    def create(self, description, callback):
        name = description.name
        klass = self._klasses[name]
        return klass.create(description, callback)
