import typing
from mitmproxy.tools.console import commandeditor
from mitmproxy.tools.console import signals


Contexts = {
    "chooser",
    "commands",
    "eventlog",
    "flowlist",
    "flowview",
    "global",
    "grideditor",
    "help",
    "keybindings",
    "options",
}


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
        self.executor = commandeditor.CommandExecutor(master)
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
