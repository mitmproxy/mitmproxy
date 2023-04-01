import mitmproxy.http
import logging
import re
import json
import os
import pathlib


# Inject a script into browser-responses for html that lets us get DOM timings, first paint time, and other metrics.
class BrowserDataAddOn:

    def __init__(self, har_capture_addon):
        file_dir = pathlib.Path(__file__).parent.parent.parent.parent.resolve()
        filepath = os.path.normpath(os.path.join(file_dir, "scripts/browsertime/browser-data.js"))
        with open(filepath, 'r') as file:
            self.browser_data_script = f'<script data-browserup=true>' + file.read() + '</script>'
            self.browser_data_script_len = len(self.browser_data_script)
            self.HarCaptureAddon = har_capture_addon

    def load(self, l):
        logging.info('Loading BrowserDataAddOn')

    def request(self, f: mitmproxy.http.HTTPFlow):
        if f.request.url.rfind('BrowserUpData') > -1:
            logging.info(f'detected URL: {f.request.url}')
            action = re.search("\/BrowserUpData/([a-zA-Z_]+)", f.request.url).group(1)
            f.metadata['blocklisted'] = True
            logging.info(f'BrowserUpData action: {action}')
            if action == 'page_info' or action == 'page_complete':
                form = f.request.multipart_form
                logging.info(f'PageTimings {form.fields}')
                data = form.fields[0][1].decode('UTF-8')
                page_timings = json.loads(data)
                self.HarCaptureAddon.add_page_info_to_har(page_timings)
                if action == 'page_complete':
                    self.HarCaptureAddon.end_page()
                    f.kill()

    def response(self, f: mitmproxy.http.HTTPFlow):
        if f.response is None or f.response.status_code != 200 or f.request.method not in ['GET', 'POST', 'PUT']:
            return

        if "content-type" in f.response.headers and "text/html" in f.response.headers["content-type"]:
            if f.response.content is not None:
                html = f.response.content.decode('utf-8')
                html = re.sub('</body', self.browser_data_script + '</body', html)
                html = re.sub('(?i)<meta[^>]+content-security-policy[^>]+>', '', html)
                f.metadata['injected_script_len'] = self.browser_data_script_len

                # <meta http-equiv="Content-Security-Policy" content="default-src 'self'">
                # if we don't delete this, customer pages may be cranky about the script
                if 'content-security-policy' in f.response.headers:
                    del f.response.headers['content-security-policy']

                f.response.text = html
