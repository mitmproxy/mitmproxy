import pyclamd
from libmproxy.flow import decoded

#http://www.eicar.org/85-0-Download.html
clamd = None

def start(context, argv=[]):
    global clamd
    clamd = pyclamd.ClamdUnixSocket()
    try:
        # test if server is reachable
        clamd.ping()
    except AttributeError, pyclamd.ConnectionError:
        # if failed, test for network socket
        clamd = pyclamd.ClamdNetworkSocket()
        clamd.ping() #fails instantly if we dont get a proper connection

    print "ClamAV running: %s" % clamd.version()

def done(ctx):
    clamd.shutdown()

def response(context, flow):
    with decoded(flow.response):
        clamd_result = clamd.scan_stream(flow.response.content)
    if clamd_result:
        print "Virus detected: ",clamd_result
        flow.response.content = "mitmproxy has detected a virus and stopped this page from loading: %s" % str(clamd_result["stream"])
        flow.response.headers["Content-Length"] = [str(len(flow.response.content))]
        flow.response.headers["Content-Type"] = ["text/html"]
        del flow.response.headers["Content-Disposition"]
        del flow.response.headers["Content-Encoding"]
        flow.response.code = 403
        flow.response.msg = "Forbidden"
