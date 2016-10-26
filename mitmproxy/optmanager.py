import contextlib
import blinker
import pprint

from mitmproxy import exceptions
from mitmproxy.utils import typecheck

"""
    The base implementation for Options.
"""


class OptManager:
    """
        .changed is a blinker Signal that triggers whenever options are
        updated. If any handler in the chain raises an exceptions.OptionsError
        exception, all changes are rolled back, the exception is suppressed,
        and the .errored signal is notified.
    """
    _initialized = False
    attributes = []

    def __new__(cls, *args, **kwargs):
        # Initialize instance._opts before __init__ is called.
        # This allows us to call super().__init__() last, which then sets
        # ._initialized = True as the final operation.
        instance = super().__new__(cls)
        instance.__dict__["_opts"] = {}
        return instance

    def __init__(self):
        self.__dict__["changed"] = blinker.Signal()
        self.__dict__["errored"] = blinker.Signal()
        self.__dict__["_initialized"] = True

    @contextlib.contextmanager
    def rollback(self, updated):
        old = self._opts.copy()
        try:
            yield
        except exceptions.OptionsError as e:
            # Notify error handlers
            self.errored.send(self, exc=e)
            # Rollback
            self.__dict__["_opts"] = old
            self.changed.send(self, updated=updated)

    def __eq__(self, other):
        return self._opts == other._opts

    def __copy__(self):
        return self.__class__(**self._opts)

    def __getattr__(self, attr):
        if attr in self._opts:
            return self._opts[attr]
        else:
            raise AttributeError("No such option: %s" % attr)

    def __setattr__(self, attr, value):
        if not self._initialized:
            self._typecheck(attr, value)
            self._opts[attr] = value
            return
        self.update(**{attr: value})

    def _typecheck(self, attr, value):
        expected_type = typecheck.get_arg_type_from_constructor_annotation(
            type(self), attr
        )
        if expected_type is None:
            return  # no type info :(
        typecheck.check_type(attr, value, expected_type)

    def keys(self):
        return set(self._opts.keys())

    def get(self, k, d=None):
        return self._opts.get(k, d)

    def update(self, **kwargs):
        updated = set(kwargs.keys())
        for k, v in kwargs.items():
            if k not in self._opts:
                raise KeyError("No such option: %s" % k)
            self._typecheck(k, v)
        with self.rollback(updated):
            self._opts.update(kwargs)
            self.changed.send(self, updated=updated)

    def setter(self, attr):
        """
            Generate a setter for a given attribute. This returns a callable
            taking a single argument.
        """
        if attr not in self._opts:
            raise KeyError("No such option: %s" % attr)

        def setter(x):
            setattr(self, attr, x)
        return setter

    def toggler(self, attr):
        """
            Generate a toggler for a boolean attribute. This returns a callable
            that takes no arguments.
        """
        if attr not in self._opts:
            raise KeyError("No such option: %s" % attr)

        def toggle():
            setattr(self, attr, not getattr(self, attr))
        return toggle

    def __repr__(self):
        options = pprint.pformat(self._opts, indent=4).strip(" {}")
        if "\n" in options:
            options = "\n    " + options + "\n"
        return "{mod}.{cls}({{{options}}})".format(
            mod=type(self).__module__,
            cls=type(self).__name__,
            options=options
        )
