import mitmproxy.http
from mitmproxy import ctx

import re

# The intention is that we can inject a script into browser-responses for html
# that lets us get DOM timings, first paint time, and other metrics. Devs and managers would like
# a graph of time to first paint over time (by release) ideally

class PagePerfScriptAddOn:
    def load(self, l):
        ctx.log.info('Loading PagePerfScriptAddon')

    def get_url(self):
        url = "http://{0}:{1}".format(
            ctx.options.listen_host or "localhost",
            ctx.options.listen_port or "8088"
        )
        return url


    def request(self, flow: mitmproxy.http.HTTPFlow):
        # Hijack CORS OPTIONS request
        if flow.request.method == "OPTIONS":
            flow.response = http.HTTPResponse.make(200, b"",
                                                   {"Access-Control-Allow-Origin": "*",
                                                    "Access-Control-Allow-Methods": "GET,POST",
                                                    "Access-Control-Allow-Headers": "Authorization",
                                                    "Access-Control-Max-Age": "1728000"})

    def response(self, flow: mitmproxy.http.HTTPFlow):
        if "content-type" in flow.response.headers and "text/html" in flow.response.headers["content-type"]:
            src_url = self.get_url() + "/browser/scripts/pageperf.js"

            flow.response.headers["Access-Control-Allow-Origin"] = "*"
            flow.response.headers["Access-Control-Allow-Methods"] = "POST,GET,OPTIONS,PUT,DELETE"

            script = f'''
                <script>if (!window.bupLoaded){{let s=document.createElement("script");s.setAttribute("src", "{src_url}");window.bupLoaded=true;document.body.appendChild(s);}}</script>
                '''

            html = flow.response.content.decode('utf-8')
            html = re.sub('</body', script + '</body', html)
            # <meta http-equiv="Content-Security-Policy" content="default-src 'self'">
            html = re.sub('(?i)<meta[^>]+content-security-policy[^>]+>', '', html)

            # if we don't delete this, customer pages may be cranky about the script
            if 'Content-Security-Policy' in flow.response.headers:
                del flow.response.headers['Content-Security-Policy']

            flow.response.text = html


addons = [
    PagePerfScriptAddOn()
]
