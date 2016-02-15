import time
from libmproxy.script import concurrent


@concurrent
def clientconnect(context, cc):
    context.log("clientconnect")


@concurrent
def serverconnect(context, sc):
    context.log("serverconnect")


@concurrent
def request(context, flow):
    time.sleep(0.1)


@concurrent
def response(context, flow):
    context.log("response")


@concurrent
def error(context, err):
    context.log("error")


@concurrent
def clientdisconnect(context, dc):
    context.log("clientdisconnect")
