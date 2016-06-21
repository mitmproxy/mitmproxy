from __future__ import absolute_import, print_function, division
import six


class Facade(object):
    def __init__(self, getobj):
        self._getobj = getobj

    if six.PY3:
        def __bool__(self):
            return bool(self._getobj())

    if six.PY2:
        def __nonzero__(self):
            return bool(self._getobj())

    def __getattr__(self, attrib):
        return getattr(self._getobj(), attrib)
