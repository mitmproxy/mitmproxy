import typing

from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import command
from mitmproxy import flow


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

    @command.command("flow.resume")
    def resume(self, flows: typing.Sequence[flow.Flow]) -> None:
        """
            Resume flows if they are intercepted.
        """
        intercepted = [i for i in flows if i.intercepted]
        for f in intercepted:
            f.resume()
        ctx.master.addons.trigger("update", intercepted)

    # FIXME: this will become view.mark later
    @command.command("flow.mark")
    def mark(self, flows: typing.Sequence[flow.Flow], val: bool) -> None:
        """
            Mark flows.
        """
        updated = []
        for i in flows:
            if i.marked != val:
                i.marked = val
                updated.append(i)
        ctx.master.addons.trigger("update", updated)

    # FIXME: this will become view.mark.toggle later
    @command.command("flow.mark.toggle")
    def mark_toggle(self, flows: typing.Sequence[flow.Flow]) -> None:
        """
            Toggle mark for flows.
        """
        for i in flows:
            i.marked = not i.marked
        ctx.master.addons.trigger("update", flows)

    @command.command("flow.kill")
    def kill(self, flows: typing.Sequence[flow.Flow]) -> None:
        """
            Kill running flows.
        """
        updated = []
        for f in flows:
            if f.killable:
                f.kill()
                updated.append(f)
        ctx.log.alert("Killed %s flows." % len(updated))
        ctx.master.addons.trigger("update", updated)

    # FIXME: this will become view.revert later
    @command.command("flow.revert")
    def revert(self, flows: typing.Sequence[flow.Flow]) -> None:
        """
            Revert flow changes.
        """
        updated = []
        for f in flows:
            if f.modified():
                f.revert()
                updated.append(f)
        ctx.log.alert("Reverted %s flows." % len(updated))
        ctx.master.addons.trigger("update", updated)
