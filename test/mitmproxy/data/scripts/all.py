import mitmproxy
record = []


def clientconnect(cc):
    mitmproxy.ctx.log("XCLIENTCONNECT")
    record.append("clientconnect")


def serverconnect(cc):
    mitmproxy.ctx.log("XSERVERCONNECT")
    record.append("serverconnect")


def request(f):
    mitmproxy.ctx.log("XREQUEST")
    record.append("request")


def response(f):
    mitmproxy.ctx.log("XRESPONSE")
    record.append("response")


def responseheaders(f):
    mitmproxy.ctx.log("XRESPONSEHEADERS")
    record.append("responseheaders")


def clientdisconnect(cc):
    mitmproxy.ctx.log("XCLIENTDISCONNECT")
    record.append("clientdisconnect")


def error(cc):
    mitmproxy.ctx.log("XERROR")
    record.append("error")
