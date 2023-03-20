import mitmproxy.http
from mitmproxy import ctx
import logging
import os
import re

# The intention is that we can inject a script into browser-responses for html
# that lets us get DOM timings, first paint time, and other metrics. Devs and managers would like
# a graph of time to first paint over time (by release) ideally


class PagePerfScriptAddOn:
    def load(self, l):
        logging.info('Loading PagePerfScriptAddon')
        self.injectable_methods = ['GET', 'POST', 'PUT']

    def get_proxy_management_url(self):
        management_port = os.environ.get('PROXY_MANAGEMENT_PORT') or ctx.options.addons_management_port or "48088"
        proxy_baseurl = ctx.options.listen_host or "127.0.0.1"
        url = "http://{0}:{1}".format(proxy_baseurl , management_port)
        return url

    def request(self, flow: mitmproxy.http.HTTPFlow):
        # Hijack CORS OPTIONS request
        if flow.request.method == "OPTIONS":
            flow.response = mitmproxy.http.Response.make(204, b"", {"Access-Control-Allow-Origin": "*",
                                                                    "Access-Control-Allow-Methods": "*",
                                                                    "Access-Control-Allow-Headers": "*",
                                                                    "Access-Control-Max-Age": "1728000"})

    def response(self, flow: mitmproxy.http.HTTPFlow):
        if flow.response is None or flow.request.method not in self.injectable_methods or flow.response.status_code != 200:
            logging.debug('Not injecting script')
            return

        if "content-type" in flow.response.headers and "text/html" in flow.response.headers["content-type"]:
            proxy_mgmt_url = self.get_proxy_management_url()
            src_url = proxy_mgmt_url + "/browser/scripts/pageperf.js"

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
