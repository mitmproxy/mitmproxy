from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import command


class Core:
    @command.command("set")
    def set(self, spec: str) -> None:
        """
            Set an option of the form "key[=value]". When the value is omitted,
            booleans are set to true, strings and integers are set to None (if
            permitted), and sequences are emptied. Boolean values can be true,
            false or toggle.
        """
        try:
            ctx.options.set(spec)
        except exceptions.OptionsError as e:
            raise exceptions.CommandError(e) from e
