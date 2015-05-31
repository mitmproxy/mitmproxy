def request(context, flow):
    f = context.duplicate_flow(flow)
    f.request.path = "/changed"
    context.replay_request(f)
