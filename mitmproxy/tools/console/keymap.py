import typing
import os

import ruamel.yaml

from mitmproxy import command
from mitmproxy.tools.console import commandexecutor
from mitmproxy.tools.console import signals
from mitmproxy import ctx
from mitmproxy import exceptions
import mitmproxy.types


class KeyBindingError(Exception):
    pass


Contexts = {
    "chooser",
    "commands",
    "commonkey",
    "dataviewer",
    "eventlog",
    "flowlist",
    "flowview",
    "global",
    "grideditor",
    "help",
    "keybindings",
    "options",
}


navkeys = [
    "m_start", "m_end", "m_next", "m_select",
    "up", "down", "page_up", "page_down",
    "left", "right"
]


class Binding:
    def __init__(self, key, command, contexts, help):
        self.key, self.command, self.contexts = key, command, sorted(contexts)
        self.help = help

    def keyspec(self):
        """
            Translate the key spec from a convenient user specification to one
            Urwid understands.
        """
        return self.key.replace("space", " ")

    def sortkey(self):
        return self.key + ",".join(self.contexts)


class Keymap:
    def __init__(self, master):
        self.executor = commandexecutor.CommandExecutor(master)
        self.keys = {}
        for c in Contexts:
            self.keys[c] = {}
        self.bindings = []

    def _check_contexts(self, contexts):
        if not contexts:
            raise ValueError("Must specify at least one context.")
        for c in contexts:
            if c not in Contexts:
                raise ValueError("Unsupported context: %s" % c)

    def add(
        self,
        key: str,
        command: str,
        contexts: typing.Sequence[str],
        help=""
    ) -> None:
        """
            Add a key to the key map.
        """
        self._check_contexts(contexts)

        for b in self.bindings:
            if b.key == key and b.command.strip() == command.strip():
                b.contexts = sorted(list(set(b.contexts + contexts)))
                if help:
                    b.help = help
                self.bind(b)
                break
        else:
            self.remove(key, contexts)
            b = Binding(key=key, command=command, contexts=contexts, help=help)
            self.bindings.append(b)
            self.bind(b)
        signals.keybindings_change.send(self)

    def remove(self, key: str, contexts: typing.Sequence[str]) -> None:
        """
            Remove a key from the key map.
        """
        self._check_contexts(contexts)
        for c in contexts:
            b = self.get(c, key)
            if b:
                self.unbind(b)
                b.contexts = [x for x in b.contexts if x != c]
                if b.contexts:
                    self.bindings.append(b)
                    self.bind(b)
        signals.keybindings_change.send(self)

    def bind(self, binding: Binding) -> None:
        for c in binding.contexts:
            self.keys[c][binding.keyspec()] = binding

    def unbind(self, binding: Binding) -> None:
        """
            Unbind also removes the binding from the list.
        """
        for c in binding.contexts:
            del self.keys[c][binding.keyspec()]
            self.bindings = [b for b in self.bindings if b != binding]

    def get(self, context: str, key: str) -> typing.Optional[Binding]:
        if context in self.keys:
            return self.keys[context].get(key, None)
        return None

    def list(self, context: str) -> typing.Sequence[Binding]:
        b = [x for x in self.bindings if context in x.contexts or context == "all"]
        single = [x for x in b if len(x.key.split()) == 1]
        multi = [x for x in b if len(x.key.split()) != 1]
        single.sort(key=lambda x: x.sortkey())
        multi.sort(key=lambda x: x.sortkey())
        return single + multi

    def handle(self, context: str, key: str) -> typing.Optional[str]:
        """
            Returns the key if it has not been handled, or None.
        """
        b = self.get(context, key) or self.get("global", key)
        if b:
            return self.executor(b.command)
        return key

    def handle_only(self, context: str, key: str) -> typing.Optional[str]:
        """
            Like handle, but ignores global bindings. Returns the key if it has
            not been handled, or None.
        """
        b = self.get(context, key)
        if b:
            return self.executor(b.command)
        return key


keyAttrs = {
    "key": lambda x: isinstance(x, str),
    "cmd": lambda x: isinstance(x, str),
    "ctx": lambda x: isinstance(x, list) and [isinstance(v, str) for v in x],
    "help": lambda x: isinstance(x, str),
}
requiredKeyAttrs = set(["key", "cmd"])


class KeymapConfig:
    defaultFile = "keys.yaml"

    @command.command("console.keymap.load")
    def keymap_load_path(self, path: mitmproxy.types.Path) -> None:
        try:
            self.load_path(ctx.master.keymap, path)  # type: ignore
        except (OSError, KeyBindingError) as e:
            raise exceptions.CommandError(
                "Could not load key bindings - %s" % e
            ) from e

    def running(self):
        p = os.path.join(os.path.expanduser(ctx.options.confdir), self.defaultFile)
        if os.path.exists(p):
            try:
                self.load_path(ctx.master.keymap, p)
            except KeyBindingError as e:
                ctx.log.error(e)

    def load_path(self, km, p):
        if os.path.exists(p) and os.path.isfile(p):
            with open(p, "rt", encoding="utf8") as f:
                try:
                    txt = f.read()
                except UnicodeDecodeError as e:
                    raise KeyBindingError(
                        "Encoding error - expected UTF8: %s: %s" % (p, e)
                    )
            try:
                vals = self.parse(txt)
            except KeyBindingError as e:
                raise KeyBindingError(
                    "Error reading %s: %s" % (p, e)
                ) from e
            for v in vals:
                user_ctxs = v.get("ctx", ["global"])
                try:
                    km._check_contexts(user_ctxs)
                    km.remove(v["key"], user_ctxs)
                    km.add(
                        key = v["key"],
                        command = v["cmd"],
                        contexts = user_ctxs,
                        help = v.get("help", None),
                    )
                except ValueError as e:
                    raise KeyBindingError(
                        "Error reading %s: %s" % (p, e)
                    ) from e

    def parse(self, text):
        try:
            data = ruamel.yaml.safe_load(text)
        except ruamel.yaml.error.YAMLError as v:
            if hasattr(v, "problem_mark"):
                snip = v.problem_mark.get_snippet()
                raise KeyBindingError(
                    "Key binding config error at line %s:\n%s\n%s" %
                    (v.problem_mark.line + 1, snip, v.problem)
                )
            else:
                raise KeyBindingError("Could not parse key bindings.")
        if not data:
            return []
        if not isinstance(data, list):
            raise KeyBindingError("Inalid keybinding config - expected a list of keys")

        for k in data:
            unknown = k.keys() - keyAttrs.keys()
            if unknown:
                raise KeyBindingError("Unknown key attributes: %s" % unknown)
            missing = requiredKeyAttrs - k.keys()
            if missing:
                raise KeyBindingError("Missing required key attributes: %s" % unknown)
            for attr in k.keys():
                if not keyAttrs[attr](k[attr]):
                    raise KeyBindingError("Invalid type for %s" % attr)

        return data
