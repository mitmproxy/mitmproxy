from __future__ import absolute_import, print_function, division

import datetime
import json
import time

import netlib.utils


def timestamp():
    """
        Returns a serializable UTC timestamp.
    """
    return time.time()


def format_timestamp(s):
    s = time.localtime(s)
    d = datetime.datetime.fromtimestamp(time.mktime(s))
    return d.strftime("%Y-%m-%d %H:%M:%S")


def format_timestamp_with_milli(s):
    d = datetime.datetime.fromtimestamp(s)
    return d.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def pretty_json(s):
    try:
        p = json.loads(s)
    except ValueError:
        return None
    return json.dumps(p, sort_keys=True, indent=4)


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
