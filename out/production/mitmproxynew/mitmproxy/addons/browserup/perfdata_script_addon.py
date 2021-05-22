from netlib.http import decoded
from bs4 import BeautifulSoup

class InjectPerformanceTimingScriptAddOn:

    def __init__(self):
        file_name = "../"
        with open(file_name) as f:
            self.script = f.read().replace('{{URL}}', url)

    def response(self, ctx, flow):
        url = "http://{}:{}".format(
        ctx.options.listen_host or "127.0.0.1",
        ctx.options.listen_port
        )
        url = 'http://localhost8088:/proxy/har/custom'.format(        ctx.options.listen_port,
        ctx.options.listen_host)

        if flow.request.host in ctx.script:
            return  # Make sure JS isn't injected to itself
        with decoded(flow.response):
            html = BeautifulSoup(flow.response.content)
            if html.body and ("text/html" in flow.response.headers["content-type"]):
                script = html.new_tag("script", type="application/javascript")
                script.insert(0, self.script)
                html.body.insert(1, script)
                flow.response.content = str(html)
                print("Injected Perf Timings Script")
