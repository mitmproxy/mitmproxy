"""An addon using the abbreviated scripting syntax."""


def request(flow):
    flow.request.headers["myheader"] = "value"
