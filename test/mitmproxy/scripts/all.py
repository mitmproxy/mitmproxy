log = []


def clientconnect(ctx, cc):
    ctx.log("XCLIENTCONNECT")
    log.append("clientconnect")


def serverconnect(ctx, cc):
    ctx.log("XSERVERCONNECT")
    log.append("serverconnect")


def request(ctx, f):
    ctx.log("XREQUEST")
    log.append("request")


def response(ctx, f):
    ctx.log("XRESPONSE")
    log.append("response")


def responseheaders(ctx, f):
    ctx.log("XRESPONSEHEADERS")
    log.append("responseheaders")


def clientdisconnect(ctx, cc):
    ctx.log("XCLIENTDISCONNECT")
    log.append("clientdisconnect")


def error(ctx, cc):
    ctx.log("XERROR")
    log.append("error")
