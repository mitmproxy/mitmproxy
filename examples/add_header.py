def response(context, flow):
    flow.response.headers["newheader"] = ["foo"]