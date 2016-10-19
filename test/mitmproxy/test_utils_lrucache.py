from mitmproxy.utils import lrucache


def test_LRUCache():
    cache = lrucache.LRUCache(2)

    class Foo:
        ran = False

        def gen(self, x):
            self.ran = True
            return x
    f = Foo()

    assert not f.ran
    assert cache.get(f.gen, 1) == 1
    assert f.ran
    f.ran = False
    assert cache.get(f.gen, 1) == 1
    assert not f.ran

    f.ran = False
    assert cache.get(f.gen, 1) == 1
    assert not f.ran
    assert cache.get(f.gen, 2) == 2
    assert cache.get(f.gen, 3) == 3
    assert f.ran

    f.ran = False
    assert cache.get(f.gen, 1) == 1
    assert f.ran

    assert len(cache.cacheList) == 2
    assert len(cache.cache) == 2
