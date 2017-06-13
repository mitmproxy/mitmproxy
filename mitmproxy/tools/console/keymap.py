import typing
from mitmproxy.tools.console import commandeditor


SupportedContexts = {
    "chooser",
    "commands",
    "eventlog",
    "flowlist",
    "flowview",
    "global",
    "grideditor",
    "help",
    "options",
}


class Binding:
    def __init__(self, key, command, contexts, help):
        self.key, self.command, self.contexts = key, command, contexts
        self.help = help

    def keyspec(self):
        """
            Translate the key spec from a convenient user specification to one
            Urwid understands.
        """
        return self.key.replace("space", " ")


class Keymap:
    def __init__(self, master):
        self.executor = commandeditor.CommandExecutor(master)
        self.keys = {}
        self.bindings = []

    def add(self, key: str, command: str, contexts: typing.Sequence[str], help="") -> None:
        """
            Add a key to the key map. If context is empty, it's considered to be
            a global binding.
        """
        if not contexts:
            raise ValueError("Must specify at least one context.")
        for c in contexts:
            if c not in SupportedContexts:
                raise ValueError("Unsupported context: %s" % c)

        b = Binding(key=key, command=command, contexts=contexts, help=help)
        self.bindings.append(b)
        self.bind(b)

    def bind(self, binding):
        for c in binding.contexts:
            d = self.keys.setdefault(c, {})
            d[binding.keyspec()] = binding.command

    def get(self, context: str, key: str) -> typing.Optional[str]:
        if context in self.keys:
            return self.keys[context].get(key, None)
        return None

    def list(self, context: str) -> typing.Sequence[Binding]:
        b = [b for b in self.bindings if context in b.contexts or context == "all"]
        b.sort(key=lambda x: x.key)
        return b

    def handle(self, context: str, key: str) -> typing.Optional[str]:
        """
            Returns the key if it has not been handled, or None.
        """
        cmd = self.get(context, key)
        if not cmd:
            cmd = self.get("global", key)
        if cmd:
            return self.executor(cmd)
        return key
