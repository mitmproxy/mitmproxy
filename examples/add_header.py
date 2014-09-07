def response(ctx, flow):
    flow.response.headers["newheader"] = ["foo"]