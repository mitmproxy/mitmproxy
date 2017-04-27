import typing
from mitmproxy.tools.console import commandeditor


class Keymap:
    def __init__(self, master):
        self.executor = commandeditor.CommandExecutor(master)
        self.keys = {}

    def add(self, key: str, command: str, context: str = "") -> None:
        """
            Add a key to the key map. If context is empty, it's considered to be
            a global binding.
        """
        d = self.keys.setdefault(context, {})
        d[key] = command

    def get(self, context: str, key: str) -> typing.Optional[str]:
        if context in self.keys:
            return self.keys[context].get(key, None)
        return None

    def handle(self, context: str, key: str) -> typing.Optional[str]:
        """
            Returns the key if it has not been handled, or None.
        """
        cmd = self.get(context, key)
        if cmd:
            return self.executor(cmd)
        if cmd != "":
            cmd = self.get("", key)
            if cmd:
                return self.executor(cmd)
        return key
