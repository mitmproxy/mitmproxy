import contextlib
import blinker
import pprint
import copy
import functools
import weakref
import os
import typing

import ruamel.yaml

from mitmproxy import exceptions
from mitmproxy.utils import typecheck

"""
    The base implementation for Options.
"""

unset = object()


class _Option:
    __slots__ = ("name", "typespec", "value", "_default", "help")

    def __init__(
        self,
        name: str,
        default: typing.Any,
        typespec: typing.Type,
        help: typing.Optional[str]
    ) -> None:
        typecheck.check_type(name, default, typespec)
        self.name = name
        self._default = default
        self.typespec = typespec
        self.value = unset
        self.help = help

    def __repr__(self):
        return "{value} [{type}]".format(value=self.current(), type=self.typespec)

    @property
    def default(self):
        return copy.deepcopy(self._default)

    def current(self) -> typing.Any:
        if self.value is unset:
            v = self.default
        else:
            v = self.value
        return copy.deepcopy(v)

    def set(self, value: typing.Any) -> None:
        typecheck.check_type(self.name, value, self.typespec)
        self.value = value

    def reset(self) -> None:
        self.value = unset

    def has_changed(self) -> bool:
        return self.value is not unset

    def __eq__(self, other) -> bool:
        for i in self.__slots__:
            if getattr(self, i) != getattr(other, i):
                return False
        return True

    def __deepcopy__(self, _):
        o = _Option(self.name, self.default, self.typespec, self.help)
        if self.has_changed():
            o.value = self.current()
        return o


class OptManager:
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
    def __init__(self):
        self.__dict__["_options"] = {}
        self.__dict__["changed"] = blinker.Signal()
        self.__dict__["errored"] = blinker.Signal()
        self.__dict__["_processed"] = {}

    def add_option(
        self,
        name: str,
        default: typing.Any,
        typespec: typing.Type,
        help: str = None
    ) -> None:
        if name in self._options:
            raise ValueError("Option %s already exists" % name)
        self._options[name] = _Option(name, default, typespec, help)

    @contextlib.contextmanager
    def rollback(self, updated):
        old = copy.deepcopy(self._options)
        try:
            yield
        except exceptions.OptionsError as e:
            # Notify error handlers
            self.errored.send(self, exc=e)
            # Rollback
            self.__dict__["_options"] = old
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
        return self._options == other._options

    def __copy__(self):
        o = OptManager()
        o.__dict__["_options"] = copy.deepcopy(self._options)
        return o

    def __getattr__(self, attr):
        if attr in self._options:
            return self._options[attr].current()
        else:
            raise AttributeError("No such option: %s" % attr)

    def __setattr__(self, attr, value):
        self.update(**{attr: value})

    def keys(self):
        return set(self._options.keys())

    def reset(self):
        """
            Restore defaults for all options.
        """
        for o in self._options.values():
            o.reset()

    def update(self, **kwargs):
        updated = set(kwargs.keys())
        with self.rollback(updated):
            for k, v in kwargs.items():
                if k not in self._options:
                    raise KeyError("No such option: %s" % k)
                self._options[k].set(v)
            self.changed.send(self, updated=updated)
        return self

    def setter(self, attr):
        """
            Generate a setter for a given attribute. This returns a callable
            taking a single argument.
        """
        if attr not in self._options:
            raise KeyError("No such option: %s" % attr)

        def setter(x):
            setattr(self, attr, x)
        return setter

    def toggler(self, attr):
        """
            Generate a toggler for a boolean attribute. This returns a callable
            that takes no arguments.
        """
        if attr not in self._options:
            raise KeyError("No such option: %s" % attr)
        o = self._options[attr]
        if o.typespec != bool:
            raise ValueError("Toggler can only be used with boolean options")

        def toggle():
            setattr(self, attr, not getattr(self, attr))
        return toggle

    def default(self, option: str) -> typing.Any:
        return self._options[option].default

    def has_changed(self, option):
        """
            Has the option changed from the default?
        """
        return self._options[option].has_changed()

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
            if k not in self._options:
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
        try:
            self.update(**data)
        except KeyError as v:
            raise exceptions.OptionsError(v)

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
                try:
                    self.load(txt)
                except exceptions.OptionsError as e:
                    raise exceptions.OptionsError(
                        "Error reading %s: %s" % (p, e)
                    )

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
        options = pprint.pformat(self._options, indent=4).strip(" {}")
        if "\n" in options:
            options = "\n    " + options + "\n"
        return "{mod}.{cls}({{{options}}})".format(
            mod=type(self).__module__,
            cls=type(self).__name__,
            options=options
        )

    def make_parser(self, parser, option, metavar=None):
        o = self._options[option]
        f = option.replace("_", "-")
        if o.typespec == bool:
            g = parser.add_mutually_exclusive_group(required=False)
            g.add_argument(
                "--%s" % f,
                action="store_true",
                dest=option,
                help=o.help
            )
            g.add_argument(
                "--no-%s" % f,
                action="store_false",
                dest=option,
                help=o.help
            )
            parser.set_defaults(**{option: o.default})
        elif o.typespec in (int, typing.Optional[int]):
            parser.add_argument(
                "--%s" % f,
                action="store",
                type=int,
                dest=option,
                help=o.help,
                metavar=metavar
            )
        elif o.typespec in (str, typing.Optional[str]):
            parser.add_argument(
                "--%s" % f,
                action="store",
                type=str,
                dest=option,
                help=o.help,
                metavar=metavar
            )
        else:
            raise ValueError("Unsupported option type: %s", o.typespec)
