from tests.market.feed.dummy import DummyFeed
from cryptomate.market import FeedDescription
from cryptomate.market.feed.factory import Factory
from pytest import raises


def no_op(*args, **kwargs):
    pass

# ----------------------------------------------------------------------------

def test_factory_create():
    ''' Basic working of factory class: pass description, get instance back '''
    factory = Factory(classes={'dummy': DummyFeed})
    feed = factory.create(FeedDescription('dummy', 'symbol', 60), callback=no_op, on_error=no_op)

    assert isinstance(feed, DummyFeed)
    assert feed.callback is no_op

    with raises(TypeError):
        factory.create({'name': 'dummy', 'symbol': 'symbol', 'period': 60})


def test_factory_register():
    ''' Class registered with a factory instance becomes creatable '''
    factory = Factory()
    with raises(ValueError):
        factory.create(FeedDescription('dummy', 'symbol', 60), callback=no_op, on_error=no_op)

    factory.register(DummyFeed)
    feed = factory.create(FeedDescription('dummy', 'symbol', 60), callback=no_op, on_error=no_op)
    assert isinstance(feed, DummyFeed)

    with raises(TypeError):
        factory.register(str)


def test_factory_isolation():
    ''' Class registered with a factory instance must not be known by another factory '''
    factoryA = Factory()
    factoryA.register(DummyFeed)

    factoryB = Factory()
    with raises(ValueError):
        factoryB.create(FeedDescription('dummy', 'symbol', 60), callback=no_op, on_error=no_op)
