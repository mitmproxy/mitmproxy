import mitmproxy.http
from mitmproxy import ctx
import logging

import re
import os

# The intention is that we can inject a script into browser-responses for html
# that lets us get DOM timings, first paint time, and other metrics. Devs and managers would like
# a graph of time to first paint over time (by release) ideally


class PagePerfScriptAddOn:
    def load(self, l):
        logging.info('Loading PagePerfScriptAddon')

    def get_proxy_management_url(self):
        url = "http://{0}:{1}".format(
            ctx.options.listen_host or "127.0.0.1",
            ctx.options.addons_management_port or "48088"
        )
        return url

    def request(self, flow: mitmproxy.http.HTTPFlow):
        # Hijack CORS OPTIONS request
        if flow.request.method == "OPTIONS":
            flow.response = mitmproxy.http.Response.make(200, b"", {"access-control-allow-origin": "*",
                                                                    "access-control-allow-methods": "GET,POST",
                                                                    "access-control-allow-headers": "Authorization",
                                                                    "access-control-max-age": "1728000"})

    def response(self, flow: mitmproxy.http.HTTPFlow):
        if flow.response is not None and "content-type" in flow.response.headers and "text/html" in flow.response.headers["content-type"]:
            proxy_mgmt_url = self.get_proxy_management_url()
            src_url = proxy_mgmt_url + "/browser/scripts/pageperf.js"

            flow.response.headers["access-control-allow-origin"] = "*"
            flow.response.headers["access-control-allow-methods"] = "POST,GET,OPTIONS,PUT,DELETE"

            script = f'''
                <script>if (!window.bupLoaded){{let s=document.createElement("script");s.setAttribute("src", "{src_url}");
                window.bupLoaded=true;window.bupURL="{proxy_mgmt_url}";document.body.appendChild(s);}}</script>
                '''

            if flow.response.content is not None:
                html = flow.response.content.decode('utf-8')
                html = re.sub('</body', script + '</body', html)

                # <meta http-equiv="Content-Security-Policy" content="default-src 'self'">
                html = re.sub('(?i)<meta[^>]+content-security-policy[^>]+>', '', html)

                # if we don't delete this, customer pages may be cranky about the script
                if 'content-security-policy' in flow.response.headers:
                    del flow.response.headers['content-security-policy']

                flow.response.text = html


addons = [
    PagePerfScriptAddOn()
]
