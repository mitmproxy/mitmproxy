from __future__ import absolute_import, print_function, division

import contextlib
import blinker
import pprint

from mitmproxy import exceptions


class Options(object):
    """
        .changed is a blinker Signal that triggers whenever options are
        updated. If any handler in the chain raises an exceptions.OptionsError
        exception, all changes are rolled back, the exception is suppressed,
        and the .errored signal is notified.
    """
    attributes = []

    def __init__(self, **kwargs):
        self.__dict__["changed"] = blinker.Signal()
        self.__dict__["errored"] = blinker.Signal()
        self.__dict__["_opts"] = dict([(i, None) for i in self.attributes])
        for k, v in kwargs.items():
            self._opts[k] = v

    @contextlib.contextmanager
    def rollback(self):
        old = self._opts.copy()
        try:
            yield
        except exceptions.OptionsError as e:
            # Notify error handlers
            self.errored.send(self, exc=e)
            # Rollback
            self.__dict__["_opts"] = old
            self.changed.send(self)

    def __eq__(self, other):
        return self._opts == other._opts

    def __copy__(self):
        return self.__class__(**self._opts)

    def __getattr__(self, attr):
        if attr in self._opts:
            return self._opts[attr]
        else:
            raise AttributeError()

    def __setattr__(self, attr, value):
        if attr not in self._opts:
            raise KeyError("No such option: %s" % attr)
        with self.rollback():
            self._opts[attr] = value
            self.changed.send(self)

    def get(self, k, d=None):
        return self._opts.get(k, d)

    def update(self, **kwargs):
        for k in kwargs:
            if k not in self._opts:
                raise KeyError("No such option: %s" % k)
        with self.rollback():
            self._opts.update(kwargs)
            self.changed.send(self)

    def __repr__(self):
        return pprint.pformat(self._opts)
