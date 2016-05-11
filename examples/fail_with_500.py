def response(context, flow):
    flow.response.status_code = 500
    flow.response.content = None
