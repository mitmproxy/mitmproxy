import contextlib
import blinker
import pprint
import inspect
import copy
import functools
import weakref
import os

import ruamel.yaml

from mitmproxy import exceptions
from mitmproxy.utils import typecheck


"""
    The base implementation for Options.
"""


class _DefaultsMeta(type):
    def __new__(cls, name, bases, namespace, **kwds):
        ret = type.__new__(cls, name, bases, dict(namespace))
        defaults = {}
        for klass in reversed(inspect.getmro(ret)):
            for p in inspect.signature(klass.__init__).parameters.values():
                if p.kind in (p.KEYWORD_ONLY, p.POSITIONAL_OR_KEYWORD):
                    if not p.default == p.empty:
                        defaults[p.name] = p.default
        ret._defaults = defaults
        return ret


class OptManager(metaclass=_DefaultsMeta):
    """
        OptManager is the base class from which Options objects are derived.
        Note that the __init__ method of all child classes must force all
        arguments to be positional only, by including a "*" argument.

        .changed is a blinker Signal that triggers whenever options are
        updated. If any handler in the chain raises an exceptions.OptionsError
        exception, all changes are rolled back, the exception is suppressed,
        and the .errored signal is notified.

        Optmanager always returns a deep copy of options to ensure that
        mutation doesn't change the option state inadvertently.
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

    def subscribe(self, func, opts):
        """
            Subscribe a callable to the .changed signal, but only for a
            specified list of options. The callable should accept arguments
            (options, updated), and may raise an OptionsError.
        """
        func = weakref.proxy(func)

        @functools.wraps(func)
        def _call(options, updated):
            if updated.intersection(set(opts)):
                try:
                    func(options, updated)
                except ReferenceError:
                    self.changed.disconnect(_call)

        # Our wrapper function goes out of scope immediately, so we have to set
        # weakrefs to false. This means we need to keep our own weakref, and
        # clean up the hook when it's gone.
        self.changed.connect(_call, weak=False)

    def __eq__(self, other):
        return self._opts == other._opts

    def __copy__(self):
        return self.__class__(**self._opts)

    def __getattr__(self, attr):
        if attr in self._opts:
            return copy.deepcopy(self._opts[attr])
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

    def reset(self):
        """
            Restore defaults for all options.
        """
        self.update(**self._defaults)

    @classmethod
    def default(klass, opt):
        return copy.deepcopy(klass._defaults[opt])

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

    def has_changed(self, option):
        """
            Has the option changed from the default?
        """
        if getattr(self, option) != self._defaults[option]:
            return True

    def save(self, path, defaults=False):
        """
            Save to path. If the destination file exists, modify it in-place.
        """
        if os.path.exists(path) and os.path.isfile(path):
            with open(path, "r") as f:
                data = f.read()
        else:
            data = ""
        data = self.serialize(data, defaults)
        with open(path, "w") as f:
            f.write(data)

    def serialize(self, text, defaults=False):
        """
            Performs a round-trip serialization. If text is not None, it is
            treated as a previous serialization that should be modified
            in-place.

            - If "defaults" is False, only options with non-default values are
              serialized. Default values in text are preserved.
            - Unknown options in text are removed.
            - Raises OptionsError if text is invalid.
        """
        data = self._load(text)
        for k in self.keys():
            if defaults or self.has_changed(k):
                data[k] = getattr(self, k)
        for k in list(data.keys()):
            if k not in self._opts:
                del data[k]
        return ruamel.yaml.round_trip_dump(data)

    def _load(self, text):
        if not text:
            return {}
        try:
            data = ruamel.yaml.load(text, ruamel.yaml.RoundTripLoader)
        except ruamel.yaml.error.YAMLError as v:
            snip = v.problem_mark.get_snippet()
            raise exceptions.OptionsError(
                "Config error at line %s:\n%s\n%s" %
                (v.problem_mark.line + 1, snip, v.problem)
            )
        if isinstance(data, str):
            raise exceptions.OptionsError("Config error - no keys found.")
        return data

    def load(self, text):
        """
            Load configuration from text, over-writing options already set in
            this object. May raise OptionsError if the config file is invalid.
        """
        data = self._load(text)
        self.update(**data)

    def load_paths(self, *paths):
        """
            Load paths in order. Each path takes precedence over the previous
            path. Paths that don't exist are ignored, errors raise an
            OptionsError.
        """
        for p in paths:
            p = os.path.expanduser(p)
            if os.path.exists(p) and os.path.isfile(p):
                with open(p, "r") as f:
                    txt = f.read()
                self.load(txt)

    def merge(self, opts):
        """
            Merge a dict of options into this object. Options that have None
            value are ignored. Lists and tuples are appended to the current
            option value.
        """
        toset = {}
        for k, v in opts.items():
            if v is not None:
                if isinstance(v, (list, tuple)):
                    toset[k] = getattr(self, k) + v
                else:
                    toset[k] = v
        self.update(**toset)

    def __repr__(self):
        options = pprint.pformat(self._opts, indent=4).strip(" {}")
        if "\n" in options:
            options = "\n    " + options + "\n"
        return "{mod}.{cls}({{{options}}})".format(
            mod=type(self).__module__,
            cls=type(self).__name__,
            options=options
        )
