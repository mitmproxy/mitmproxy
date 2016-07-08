import mitmproxy
log = []


def clientconnect(cc):
    mitmproxy.log("XCLIENTCONNECT")
    log.append("clientconnect")


def serverconnect(cc):
    mitmproxy.log("XSERVERCONNECT")
    log.append("serverconnect")


def request(f):
    mitmproxy.log("XREQUEST")
    log.append("request")


def response(f):
    mitmproxy.log("XRESPONSE")
    log.append("response")


def responseheaders(f):
    mitmproxy.log("XRESPONSEHEADERS")
    log.append("responseheaders")


def clientdisconnect(cc):
    mitmproxy.log("XCLIENTDISCONNECT")
    log.append("clientdisconnect")


def error(cc):
    mitmproxy.log("XERROR")
    log.append("error")
