from __future__ import annotations

import contextlib
import copy
import pprint
import textwrap
import weakref
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Optional
from typing import TextIO

import ruamel.yaml

from mitmproxy import exceptions
from mitmproxy.utils import signals
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
        typespec: type | object,  # object for Optional[x], which is not a type.
        default: Any,
        help: str,
        choices: Sequence[str] | None,
    ) -> None:
        typecheck.check_option_type(name, default, typespec)
        self.name = name
        self.typespec = typespec
        self._default = default
        self.value = unset
        self.help = textwrap.dedent(help).strip().replace("\n", " ")
        self.choices = choices

    def __repr__(self):
        return f"{self.current()} [{self.typespec}]"

    @property
    def default(self):
        return copy.deepcopy(self._default)

    def current(self) -> Any:
        if self.value is unset:
            v = self.default
        else:
            v = self.value
        return copy.deepcopy(v)

    def set(self, value: Any) -> None:
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
        o = _Option(self.name, self.typespec, self.default, self.help, self.choices)
        if self.has_changed():
            o.value = self.current()
        return o


@dataclass
class _UnconvertedStrings:
    val: list[str]


def _sig_changed_spec(updated: set[str]) -> None:  # pragma: no cover
    ...  # expected function signature for OptManager.changed receivers.


def _sig_errored_spec(exc: Exception) -> None:  # pragma: no cover
    ...  # expected function signature for OptManager.errored receivers.


class OptManager:
    """
    OptManager is the base class from which Options objects are derived.

    .changed is a Signal that triggers whenever options are
    updated. If any handler in the chain raises an exceptions.OptionsError
    exception, all changes are rolled back, the exception is suppressed,
    and the .errored signal is notified.

    Optmanager always returns a deep copy of options to ensure that
    mutation doesn't change the option state inadvertently.
    """

    def __init__(self) -> None:
        self.deferred: dict[str, Any] = {}
        self.changed = signals.SyncSignal(_sig_changed_spec)
        self.changed.connect(self._notify_subscribers)
        self.errored = signals.SyncSignal(_sig_errored_spec)
        self._subscriptions: list[tuple[weakref.ref[Callable], set[str]]] = []
        # Options must be the last attribute here - after that, we raise an
        # error for attribute assignment to unknown options.
        self._options: dict[str, Any] = {}

    def add_option(
        self,
        name: str,
        typespec: type | object,
        default: Any,
        help: str,
        choices: Sequence[str] | None = None,
    ) -> None:
        self._options[name] = _Option(name, typespec, default, help, choices)
        self.changed.send(updated={name})

    @contextlib.contextmanager
    def rollback(self, updated, reraise=False):
        old = copy.deepcopy(self._options)
        try:
            yield
        except exceptions.OptionsError as e:
            # Notify error handlers
            self.errored.send(exc=e)
            # Rollback
            self.__dict__["_options"] = old
            self.changed.send(updated=updated)
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

        self._subscriptions.append((signals.make_weak_ref(func), set(opts)))

    def _notify_subscribers(self, updated) -> None:
        cleanup = False
        for ref, opts in self._subscriptions:
            callback = ref()
            if callback is not None:
                if opts & updated:
                    callback(self, updated)
            else:
                cleanup = True

        if cleanup:
            self.__dict__["_subscriptions"] = [
                (ref, opts) for (ref, opts) in self._subscriptions if ref() is not None
            ]

    def __eq__(self, other):
        if isinstance(other, OptManager):
            return self._options == other._options
        return False

    def __deepcopy__(self, memodict=None):
        o = OptManager()
        o.__dict__["_options"] = copy.deepcopy(self._options, memodict)
        return o

    __copy__ = __deepcopy__

    def __getattr__(self, attr):
        if attr in self._options:
            return self._options[attr].current()
        else:
            raise AttributeError("No such option: %s" % attr)

    def __setattr__(self, attr, value):
        # This is slightly tricky. We allow attributes to be set on the instance
        # until we have an _options attribute. After that, assignment is sent to
        # the update function, and will raise an error for unknown options.
        opts = self.__dict__.get("_options")
        if not opts:
            super().__setattr__(attr, value)
        else:
            self.update(**{attr: value})

    def keys(self):
        return set(self._options.keys())

    def items(self):
        return self._options.items()

    def __contains__(self, k):
        return k in self._options

    def reset(self):
        """
        Restore defaults for all options.
        """
        for o in self._options.values():
            o.reset()
        self.changed.send(updated=set(self._options.keys()))

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
                self.changed.send(updated=updated)
        return unknown

    def update_defer(self, **kwargs):
        unknown = self.update_known(**kwargs)
        self.deferred.update(unknown)

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

    def default(self, option: str) -> Any:
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
            mod=type(self).__module__, cls=type(self).__name__, options=options
        )

    def set(self, *specs: str, defer: bool = False) -> None:
        """
        Takes a list of set specification in standard form (option=value).
        Options that are known are updated immediately. If defer is true,
        options that are not known are deferred, and will be set once they
        are added.

        May raise an `OptionsError` if a value is malformed or an option is unknown and defer is False.
        """
        # First, group specs by option name.
        unprocessed: dict[str, list[str]] = {}
        for spec in specs:
            if "=" in spec:
                name, value = spec.split("=", maxsplit=1)
                unprocessed.setdefault(name, []).append(value)
            else:
                unprocessed.setdefault(spec, [])

        # Second, convert values to the correct type.
        processed: dict[str, Any] = {}
        for name in list(unprocessed.keys()):
            if name in self._options:
                processed[name] = self._parse_setval(
                    self._options[name], unprocessed.pop(name)
                )

        # Third, stash away unrecognized options or complain about them.
        if defer:
            self.deferred.update(
                {k: _UnconvertedStrings(v) for k, v in unprocessed.items()}
            )
        elif unprocessed:
            raise exceptions.OptionsError(
                f"Unknown option(s): {', '.join(unprocessed)}"
            )

        # Finally, apply updated options.
        self.update(**processed)

    def process_deferred(self) -> None:
        """
        Processes options that were deferred in previous calls to set, and
        have since been added.
        """
        update: dict[str, Any] = {}
        for optname, value in self.deferred.items():
            if optname in self._options:
                if isinstance(value, _UnconvertedStrings):
                    value = self._parse_setval(self._options[optname], value.val)
                update[optname] = value
        self.update(**update)
        for k in update.keys():
            del self.deferred[k]

    def _parse_setval(self, o: _Option, values: list[str]) -> Any:
        """
        Convert a string to a value appropriate for the option type.
        """
        if o.typespec == Sequence[str]:
            return values
        if len(values) > 1:
            raise exceptions.OptionsError(
                f"Received multiple values for {o.name}: {values}"
            )

        optstr: str | None
        if values:
            optstr = values[0]
        else:
            optstr = None

        if o.typespec in (str, Optional[str]):
            if o.typespec == str and optstr is None:
                raise exceptions.OptionsError(f"Option is required: {o.name}")
            return optstr
        elif o.typespec in (int, Optional[int]):
            if optstr:
                try:
                    return int(optstr)
                except ValueError:
                    raise exceptions.OptionsError(f"Not an integer: {optstr}")
            elif o.typespec == int:
                raise exceptions.OptionsError(f"Option is required: {o.name}")
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
                    'Boolean must be "true", "false", or have the value omitted (a synonym for "true").'
                )
        raise NotImplementedError(f"Unsupported option type: {o.typespec}")

    def make_parser(self, parser, optname, metavar=None, short=None):
        """
        Auto-Create a command-line parser entry for a named option. If the
        option does not exist, it is ignored.
        """
        if optname not in self._options:
            return

        o = self._options[optname]

        def mkf(x, s):
            x = x.replace("_", "-")
            f = ["--%s" % x]
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
            g.add_argument(*onf, action="store_true", dest=optname, help=o.help)
            parser.set_defaults(**{optname: None})
        elif o.typespec in (int, Optional[int]):
            parser.add_argument(
                *flags,
                action="store",
                type=int,
                dest=optname,
                help=o.help,
                metavar=metavar,
            )
        elif o.typespec in (str, Optional[str]):
            parser.add_argument(
                *flags,
                action="store",
                type=str,
                dest=optname,
                help=o.help,
                metavar=metavar,
                choices=o.choices,
            )
        elif o.typespec == Sequence[str]:
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


def dump_defaults(opts, out: TextIO):
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
            t = typecheck.typespec_to_str(o.typespec)
            txt += " Type %s." % t

        txt = "\n".join(textwrap.wrap(txt))
        s.yaml_set_comment_before_after_key(k, before="\n" + txt)
    return ruamel.yaml.YAML().dump(s, out)


def dump_dicts(opts, keys: Iterable[str] | None = None) -> dict:
    """
    Dumps the options into a list of dict object.

    Return: A list like: { "anticache": { type: "bool", default: false, value: true, help: "help text"} }
    """
    options_dict = {}
    if keys is None:
        keys = opts.keys()
    for k in sorted(keys):
        o = opts._options[k]
        t = typecheck.typespec_to_str(o.typespec)
        option = {
            "type": t,
            "default": o.default,
            "value": o.current(),
            "help": o.help,
            "choices": o.choices,
        }
        options_dict[k] = option
    return options_dict


def parse(text):
    if not text:
        return {}
    try:
        yaml = ruamel.yaml.YAML(typ="safe", pure=True)
        data = yaml.load(text)
    except ruamel.yaml.error.YAMLError as v:
        if hasattr(v, "problem_mark"):
            snip = v.problem_mark.get_snippet()
            raise exceptions.OptionsError(
                "Config error at line %s:\n%s\n%s"
                % (v.problem_mark.line + 1, snip, getattr(v, "problem", ""))
            )
        else:
            raise exceptions.OptionsError("Could not parse options.")
    if isinstance(data, str):
        raise exceptions.OptionsError("Config error - no keys found.")
    elif data is None:
        return {}
    return data


def load(opts: OptManager, text: str, cwd: Path | str | None = None) -> None:
    """
    Load configuration from text, over-writing options already set in
    this object. May raise OptionsError if the config file is invalid.
    """
    data = parse(text)

    scripts = data.get("scripts")
    if scripts is not None and cwd is not None:
        data["scripts"] = [
            str(relative_path(Path(path), relative_to=Path(cwd))) for path in scripts
        ]

    opts.update_defer(**data)


def load_paths(opts: OptManager, *paths: Path | str) -> None:
    """
    Load paths in order. Each path takes precedence over the previous
    path. Paths that don't exist are ignored, errors raise an
    OptionsError.
    """
    for p in paths:
        p = Path(p).expanduser()
        if p.exists() and p.is_file():
            with p.open(encoding="utf8") as f:
                try:
                    txt = f.read()
                except UnicodeDecodeError as e:
                    raise exceptions.OptionsError(f"Error reading {p}: {e}")
            try:
                load(opts, txt, cwd=p.absolute().parent)
            except exceptions.OptionsError as e:
                raise exceptions.OptionsError(f"Error reading {p}: {e}")


def serialize(
    opts: OptManager, file: TextIO, text: str, defaults: bool = False
) -> None:
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

    ruamel.yaml.YAML().dump(data, file)


def save(opts: OptManager, path: Path | str, defaults: bool = False) -> None:
    """
    Save to path. If the destination file exists, modify it in-place.

    Raises OptionsError if the existing data is corrupt.
    """
    path = Path(path).expanduser()
    if path.exists() and path.is_file():
        with path.open(encoding="utf8") as f:
            try:
                data = f.read()
            except UnicodeDecodeError as e:
                raise exceptions.OptionsError(f"Error trying to modify {path}: {e}")
    else:
        data = ""

    with path.open("w", encoding="utf8") as f:
        serialize(opts, f, data, defaults)


def relative_path(script_path: Path | str, *, relative_to: Path | str) -> Path:
    """
    Make relative paths found in config files relative to said config file,
    instead of relative to where the command is ran.
    """
    script_path = Path(script_path)
    # Edge case when $HOME is not an absolute path
    if script_path.expanduser() != script_path and not script_path.is_absolute():
        script_path = script_path.expanduser().absolute()
    return (relative_to / script_path.expanduser()).absolute()
