from mitmproxy import ctx


def request(flow):
    # Avoid an infinite loop by not replaying already replayed requests
    if flow.request.is_replay:
        return
    flow = flow.copy()
    # Only interactive tools have a view. If we have one, add a duplicate entry
    # for our flow.
    if "view" in ctx.master.addons:
        ctx.master.commands.call("view.flows.add", [flow])
    flow.request.path = "/changed"
    ctx.master.commands.call("replay.client", [flow])
