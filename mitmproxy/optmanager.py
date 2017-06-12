import contextlib
import blinker
import blinker._saferef
import pprint
import copy
import functools
import os
import typing
import textwrap

import ruamel.yaml

from mitmproxy import exceptions
from mitmproxy.utils import typecheck

"""
    The base implementation for Options.
"""

unset = object()


class _Option:
    __slots__ = ("name", "typespec", "value", "_default", "choices", "help")

    def __init__(
        self,
        name: str,
        typespec: type,
        default: typing.Any,
        help: str,
        choices: typing.Optional[typing.Sequence[str]]
    ) -> None:
        typecheck.check_option_type(name, default, typespec)
        self.name = name
        self.typespec = typespec
        self._default = default
        self.value = unset
        self.help = textwrap.dedent(help).strip().replace("\n", " ")
        self.choices = choices

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
        typecheck.check_option_type(self.name, value, self.typespec)
        self.value = value

    def reset(self) -> None:
        self.value = unset

    def has_changed(self) -> bool:
        return self.current() != self.default

    def __eq__(self, other) -> bool:
        for i in self.__slots__:
            if getattr(self, i) != getattr(other, i):
                return False
        return True

    def __deepcopy__(self, _):
        o = _Option(
            self.name, self.typespec, self.default, self.help, self.choices
        )
        if self.has_changed():
            o.value = self.current()
        return o


class OptManager:
    """
        OptManager is the base class from which Options objects are derived.

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
        typespec: type,
        default: typing.Any,
        help: str,
        choices: typing.Optional[typing.Sequence[str]] = None
    ) -> None:
        self._options[name] = _Option(name, typespec, default, help, choices)

    @contextlib.contextmanager
    def rollback(self, updated, reraise=False):
        old = copy.deepcopy(self._options)
        try:
            yield
        except exceptions.OptionsError as e:
            # Notify error handlers
            self.errored.send(self, exc=e)
            # Rollback
            self.__dict__["_options"] = old
            self.changed.send(self, updated=updated)
            if reraise:
                raise e

    def subscribe(self, func, opts):
        """
            Subscribe a callable to the .changed signal, but only for a
            specified list of options. The callable should accept arguments
            (options, updated), and may raise an OptionsError.

            The event will automatically be unsubscribed if the callable goes out of scope.
        """
        for i in opts:
            if i not in self._options:
                raise exceptions.OptionsError("No such option: %s" % i)

        # We reuse blinker's safe reference functionality to cope with weakrefs
        # to bound methods.
        func = blinker._saferef.safe_ref(func)

        @functools.wraps(func)
        def _call(options, updated):
            if updated.intersection(set(opts)):
                f = func()
                if f:
                    f(options, updated)
                else:
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

    def __contains__(self, k):
        return k in self._options

    def reset(self):
        """
            Restore defaults for all options.
        """
        for o in self._options.values():
            o.reset()
        self.changed.send(self, updated=set(self._options.keys()))

    def update_known(self, **kwargs):
        """
            Update and set all known options from kwargs. Returns a dictionary
            of unknown options.
        """
        known, unknown = {}, {}
        for k, v in kwargs.items():
            if k in self._options:
                known[k] = v
            else:
                unknown[k] = v
        updated = set(known.keys())
        if updated:
            with self.rollback(updated, reraise=True):
                for k, v in known.items():
                    self._options[k].set(v)
                self.changed.send(self, updated=updated)
        return unknown

    def update(self, **kwargs):
        u = self.update_known(**kwargs)
        if u:
            raise KeyError("Unknown options: %s" % ", ".join(u.keys()))

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

    def set(self, *spec):
        vals = {}
        for i in spec:
            vals.update(self._setspec(i))
        self.update(**vals)

    def parse_setval(self, optname: str, optstr: typing.Optional[str]) -> typing.Any:
        """
            Convert a string to a value appropriate for the option type.
        """
        if optname not in self._options:
            raise exceptions.OptionsError("No such option %s" % optname)
        o = self._options[optname]

        if o.typespec in (str, typing.Optional[str]):
            return optstr
        elif o.typespec in (int, typing.Optional[int]):
            if optstr:
                try:
                    return int(optstr)
                except ValueError:
                    raise exceptions.OptionsError("Not an integer: %s" % optstr)
            elif o.typespec == int:
                raise exceptions.OptionsError("Option is required: %s" % optname)
            else:
                return None
        elif o.typespec == bool:
            if optstr == "toggle":
                return not o.current()
            if not optstr or optstr == "true":
                return True
            elif optstr == "false":
                return False
            else:
                raise exceptions.OptionsError(
                    "Boolean must be \"true\", \"false\", or have the value " "omitted (a synonym for \"true\")."
                )
        elif o.typespec == typing.Sequence[str]:
            if not optstr:
                return []
            else:
                return getattr(self, optname) + [optstr]
        raise NotImplementedError("Unsupported option type: %s", o.typespec)

    def _setspec(self, spec):
        d = {}
        parts = spec.split("=", maxsplit=1)
        if len(parts) == 1:
            optname, optval = parts[0], None
        else:
            optname, optval = parts[0], parts[1]
        d[optname] = self.parse_setval(optname, optval)
        return d

    def make_parser(self, parser, optname, metavar=None, short=None):
        o = self._options[optname]

        def mkf(l, s):
            l = l.replace("_", "-")
            f = ["--%s" % l]
            if s:
                f.append("-" + s)
            return f

        flags = mkf(optname, short)

        if o.typespec == bool:
            g = parser.add_mutually_exclusive_group(required=False)
            onf = mkf(optname, None)
            offf = mkf("no-" + optname, None)
            # The short option for a bool goes to whatever is NOT the default
            if short:
                if o.default:
                    offf = mkf("no-" + optname, short)
                else:
                    onf = mkf(optname, short)
            g.add_argument(
                *offf,
                action="store_false",
                dest=optname,
            )
            g.add_argument(
                *onf,
                action="store_true",
                dest=optname,
                help=o.help
            )
            parser.set_defaults(**{optname: None})
        elif o.typespec in (int, typing.Optional[int]):
            parser.add_argument(
                *flags,
                action="store",
                type=int,
                dest=optname,
                help=o.help,
                metavar=metavar,
            )
        elif o.typespec in (str, typing.Optional[str]):
            parser.add_argument(
                *flags,
                action="store",
                type=str,
                dest=optname,
                help=o.help,
                metavar=metavar,
                choices=o.choices
            )
        elif o.typespec == typing.Sequence[str]:
            parser.add_argument(
                *flags,
                action="append",
                type=str,
                dest=optname,
                help=o.help + " May be passed multiple times.",
                metavar=metavar,
                choices=o.choices,
            )
        else:
            raise ValueError("Unsupported option type: %s", o.typespec)


def dump_defaults(opts):
    """
        Dumps an annotated file with all options.
    """
    # Sort data
    s = ruamel.yaml.comments.CommentedMap()
    for k in sorted(opts.keys()):
        o = opts._options[k]
        s[k] = o.default
        txt = o.help.strip()

        if o.choices:
            txt += " Valid values are %s." % ", ".join(repr(c) for c in o.choices)
        else:
            if o.typespec in (str, int, bool):
                t = o.typespec.__name__
            elif o.typespec == typing.Optional[str]:
                t = "optional str"
            elif o.typespec == typing.Sequence[str]:
                t = "sequence of str"
            else:  # pragma: no cover
                raise NotImplementedError
            txt += " Type %s." % t

        txt = "\n".join(textwrap.wrap(txt))
        s.yaml_set_comment_before_after_key(k, before = "\n" + txt)
    return ruamel.yaml.round_trip_dump(s)


def dump_dicts(opts):
    """
        Dumps the options into a list of dict object.

        Return: A list like: [ { name: "anticahce", type: "bool", default: false, value: true, help: "help text"}]
    """
    options_list = []
    for k in sorted(opts.keys()):
        o = opts._options[k]
        option = {'name': k, 'type': o.typespec.__name__, 'default': o.default, 'value': o.current(), 'help': o.help.strip()}
        options_list.append(option)
    return options_list


def parse(text):
    if not text:
        return {}
    try:
        data = ruamel.yaml.load(text, ruamel.yaml.RoundTripLoader)
    except ruamel.yaml.error.YAMLError as v:
        if hasattr(v, "problem_mark"):
            snip = v.problem_mark.get_snippet()
            raise exceptions.OptionsError(
                "Config error at line %s:\n%s\n%s" %
                (v.problem_mark.line + 1, snip, v.problem)
            )
        else:
            raise exceptions.OptionsError("Could not parse options.")
    if isinstance(data, str):
        raise exceptions.OptionsError("Config error - no keys found.")
    return data


def load(opts, text):
    """
        Load configuration from text, over-writing options already set in
        this object. May raise OptionsError if the config file is invalid.

        Returns a dictionary of all unknown options.
    """
    data = parse(text)
    return opts.update_known(**data)


def load_paths(opts, *paths):
    """
        Load paths in order. Each path takes precedence over the previous
        path. Paths that don't exist are ignored, errors raise an
        OptionsError.

        Returns a dictionary of unknown options.
    """
    ret = {}
    for p in paths:
        p = os.path.expanduser(p)
        if os.path.exists(p) and os.path.isfile(p):
            with open(p, "rt", encoding="utf8") as f:
                try:
                    txt = f.read()
                except UnicodeDecodeError as e:
                    raise exceptions.OptionsError(
                        "Error reading %s: %s" % (p, e)
                    )
            try:
                ret.update(load(opts, txt))
            except exceptions.OptionsError as e:
                raise exceptions.OptionsError(
                    "Error reading %s: %s" % (p, e)
                )
    return ret


def serialize(opts, text, defaults=False):
    """
        Performs a round-trip serialization. If text is not None, it is
        treated as a previous serialization that should be modified
        in-place.

        - If "defaults" is False, only options with non-default values are
            serialized. Default values in text are preserved.
        - Unknown options in text are removed.
        - Raises OptionsError if text is invalid.
    """
    data = parse(text)
    for k in opts.keys():
        if defaults or opts.has_changed(k):
            data[k] = getattr(opts, k)
    for k in list(data.keys()):
        if k not in opts._options:
            del data[k]
    return ruamel.yaml.round_trip_dump(data)


def save(opts, path, defaults=False):
    """
        Save to path. If the destination file exists, modify it in-place.

        Raises OptionsError if the existing data is corrupt.
    """
    if os.path.exists(path) and os.path.isfile(path):
        with open(path, "rt", encoding="utf8") as f:
            try:
                data = f.read()
            except UnicodeDecodeError as e:
                raise exceptions.OptionsError(
                    "Error trying to modify %s: %s" % (path, e)
                )
    else:
        data = ""
    data = serialize(opts, data, defaults)
    with open(path, "wt", encoding="utf8") as f:
        f.write(data)
