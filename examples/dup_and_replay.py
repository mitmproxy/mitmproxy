def request(ctx, flow):
   f = ctx.duplicate_flow(flow)
   f.request.path = "/changed"
   ctx.replay_request(f)
