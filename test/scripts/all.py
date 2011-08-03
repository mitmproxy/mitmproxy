log = []
def clientconnect(ctx, cc):
    ctx.log("XCLIENTCONNECT")
    log.append("clientconnect")

def request(ctx, r):
    ctx.log("XREQUEST")
    log.append("request")

def response(ctx, r):
    ctx.log("XRESPONSE")
    log.append("response")

def clientdisconnect(ctx, cc):
    ctx.log("XCLIENTDISCONNECT")
    log.append("clientdisconnect")

def error(ctx, cc):
    ctx.log("XERROR")
    log.append("error")
