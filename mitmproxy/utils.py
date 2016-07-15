from __future__ import absolute_import, print_function, division

import netlib.utils


pkg_data = netlib.utils.Data(__name__)


class LRUCache:

    """
        A simple LRU cache for generated values.
    """

    def __init__(self, size=100):
        self.size = size
        self.cache = {}
        self.cacheList = []

    def get(self, gen, *args):
        """
            gen: A (presumably expensive) generator function. The identity of
            gen is NOT taken into account by the cache.
            *args: A list of immutable arguments, used to establish identiy by
            *the cache, and passed to gen to generate values.
        """
        if args in self.cache:
            self.cacheList.remove(args)
            self.cacheList.insert(0, args)
            return self.cache[args]
        else:
            ret = gen(*args)
            self.cacheList.insert(0, args)
            self.cache[args] = ret
            if len(self.cacheList) > self.size:
                d = self.cacheList.pop()
                self.cache.pop(d)
            return ret


def log_tier(level):
    return dict(error=0, warn=1, info=2, debug=3).get(level)
