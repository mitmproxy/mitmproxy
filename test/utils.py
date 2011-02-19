from libmproxy import proxy, utils, filt, flow

def treq(conn=None):
    if not conn:
        conn = proxy.ClientConnect(("address", 22))
    headers = utils.Headers()
    headers["header"] = ["qvalue"]
    return proxy.Request(conn, "host", 80, "http", "GET", "/path", headers, "content")


def tresp(req=None):
    if not req:
        req = treq()
    headers = utils.Headers()
    headers["header_response"] = ["svalue"]
    return proxy.Response(req, 200, "message", headers, "content_response")


def tflow():
    r = treq()
    return flow.Flow(r)

