from functools import lru_cache

def test_LRUCache():

    class Foo:
        ran = False

        @lru_cache(maxsize=2)
        def gen(self, x):
            self.ran = True
            return x
    f = Foo()

    assert not f.ran
    assert f.gen(1) == 1
    assert f.ran
    f.ran = False
    assert f.gen(1) == 1
    assert not f.ran

    f.ran = False
    assert f.gen(1) == 1
    assert not f.ran
    assert f.gen(2) == 2
    assert f.gen(3) == 3
    assert f.ran

    f.ran = False
    assert f.gen(1) == 1
    assert f.ran
