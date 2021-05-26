import typing
from mitmproxy import command, flow, ctx
from mitmproxy.hooks import UpdateHook


class Comment:
    @command.command("flow.comment")
    def comment(self, flow: typing.Sequence[flow.Flow], comment: str) -> None:
        "Add a comment to a flow"

        updated = []
        for f in flow:
            f.comment = comment
            updated.append(f)

        ctx.master.addons.trigger(UpdateHook(updated))
