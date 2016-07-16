import mitmproxy
log = []


def clientconnect(cc):
    mitmproxy.ctx.log("XCLIENTCONNECT")
    log.append("clientconnect")


def serverconnect(cc):
    mitmproxy.ctx.log("XSERVERCONNECT")
    log.append("serverconnect")


def request(f):
    mitmproxy.ctx.log("XREQUEST")
    log.append("request")


def response(f):
    mitmproxy.ctx.log("XRESPONSE")
    log.append("response")


def responseheaders(f):
    mitmproxy.ctx.log("XRESPONSEHEADERS")
    log.append("responseheaders")


def clientdisconnect(cc):
    mitmproxy.ctx.log("XCLIENTDISCONNECT")
    log.append("clientdisconnect")


def error(cc):
    mitmproxy.ctx.log("XERROR")
    log.append("error")
