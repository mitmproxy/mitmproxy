from bs4 import BeautifulSoup
from mitmproxy import ctx

# This class is WIP, but the intention is that we can inject a script into browser-requests for html
# that lets us get DOM timings, first paint time, and other metrics. There is less need for customers to have
# this ability now that selenium is going to offer many of these things, though. Since we dont'
# know when they are running selenium or cypress, or something else, we can still use our own capability to get
# these timings which is useful for monitoring and baseline performance monitoring. Devs and managers would like
# a graph of time to first paint over time (by release) ideally


class InjectPerformanceTimingScriptAddOn:

    def __init__(self):
        file_name = "../"
        with open(file_name) as f:
            self.script = f.read().replace('{{URL}}', self.get_url())

    def get_url(self):
        url = "http://{0}:{1}".format(
            ctx.options.listen_host or "127.0.0.1",
            ctx.options.listen_port
        )
        return url

    def response(self, ctx, flow):
        if flow.request.host in ctx.script:
            return  # Make sure JS isn't injected to itself

            html = BeautifulSoup(flow.response.content.decode('utf-8'))
            if html.body and ("text/html" in flow.response.headers["content-type"]):
                script = html.new_tag("script", type="application/javascript")
                script.insert(0, self.script)
                html.body.insert(1, script)
                flow.response.content = str(html)
                print("Injected Perf Timings Script")
