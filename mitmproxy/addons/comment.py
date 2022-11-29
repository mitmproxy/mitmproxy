from collections.abc import Sequence

from mitmproxy import command
from mitmproxy import ctx
from mitmproxy import flow
from mitmproxy.hooks import UpdateHook


class Comment:
    @command.command("flow.comment")
    def comment(self, flow: Sequence[flow.Flow], comment: str) -> None:
        "Add a comment to a flow"

        updated = []
        for f in flow:
            f.comment = comment
            updated.append(f)

        ctx.master.addons.trigger(UpdateHook(updated))
