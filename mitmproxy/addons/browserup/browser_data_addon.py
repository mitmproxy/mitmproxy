import base64
import hashlib
import json
import logging
import os
import pathlib
import re
import time

import mitmproxy.http


# Inject a script into browser-responses for html that lets us get DOM timings, first paint time, and other metrics.
class BrowserDataAddOn:
    def __init__(self, har_capture_addon):
        self.handshaked = False
        file_dir = pathlib.Path(__file__).parent.parent.parent.parent.resolve()
        filepath = os.path.normpath(
            os.path.join(file_dir, "scripts/browsertime/browser-data.min.js")
        )
        with open(filepath, "r") as file:
            self.browser_data_script = (
                f"<script data-browserup=true>" + file.read() + "</script>"
            )
            self.browser_data_script_len = len(self.browser_data_script)
            self.HarCaptureAddon = har_capture_addon

    def websocket_message(self, f: mitmproxy.http.HTTPFlow):
        logging.info(f"websocket_message: {f.request.url}")
        assert f.websocket is not None
        if "BrowserUpData" in f.request.url:
            message = f.websocket.messages[-1]
            content = message.content
            message.drop()

            try:
                data = json.loads(content)
                logging.info(data)
                self._process_browserup_data(data)
            except json.JSONDecodeError:
                logging.error("Invalid JSON string")

    def request(self, f: mitmproxy.http.HTTPFlow):
        logging.info(f"request: {f.request.url}")
        if "BrowserUpData" in f.request.url:
            # Generate the handshake response
            websocket_key = f.request.headers.get("Sec-WebSocket-Key", "")
            websocket_accept = self._compute_websocket_accept_value(websocket_key)
            response_headers = (
                (b"Upgrade", b"websocket"),
                (b"Connection", b"Upgrade"),
                (b"Sec-WebSocket-Accept", websocket_accept.encode()),
            )

            timestamp_start = time.time()
            timestamp_end = timestamp_start
            self.handshaked = True

            f.response = mitmproxy.http.Response(
                http_version=f.request.http_version.encode("ascii", "strict"),
                status_code=101,
                reason=b"Switching Protocols",
                headers=response_headers,
                content=b"",
                trailers=(),
                timestamp_start=timestamp_start,
                timestamp_end=timestamp_end,
            )
            f.server_conn.timestamp_start = None

    def response(self, f: mitmproxy.http.HTTPFlow):
        if self._is_full_html_page(f):
            self._inject_data_script(f)

    def _inject_data_script(self, f: mitmproxy.http.HTTPFlow):
        assert f.response is not None
        assert f.response.content is not None
        html = f.response.content.decode("utf-8")
        # html = re.sub('(?i)<meta[^>]+content-security-policy[^>]+>', '', html)
        html = re.sub("</body", self.browser_data_script + "</body", html)
        f.metadata["injected_script_len"] = self.browser_data_script_len

        # <meta http-equiv="Content-Security-Policy" content="default-src 'self'">
        # if we don't delete this, customer pages may be cranky about the script
        if "content-security-policy" in f.response.headers:
            del f.response.headers["content-security-policy"]

        f.response.text = html

    def _is_full_html_page(self, f: mitmproxy.http.HTTPFlow):
        logging.info("Evaluating injection for {}".format(f.request.url))
        if f.response is None or f.response.content is None:
            logging.info("Evaluating injection false for content")
            return False

        if f.response.status_code != 200 or f.request.method not in [
            "GET",
            "POST",
            "PUT",
        ]:
            logging.info("Evaluating injection for response false for meth or code")
            return False

        if (
            "content-type" in f.response.headers
            and "text/html" not in f.response.headers["content-type"]
        ):
            logging.info("Evaluating injection for response false for content type")
            return False

        if (
            "content-length" in f.response.headers
            and int(f.response.headers["content-length"]) < 100
        ):
            logging.info("Evaluating injection for response false for content length")
            return False

        html = f.response.content.decode("utf-8", "ignore")
        logging.info("Evaluating injection for response false for raw len")
        if len(html) < 100:
            return False

        if "<html" not in html or "<head" not in html or "<body" not in html:
            logging.info("Evaluating injection for response false for missing html tag")
            return False

        logging.info("Injecting for {}".format(f.request.url))
        return True

    def _process_browserup_data(self, data):
        operation = data["operation"]
        # delete the operation key
        del data["operation"]
        data = data["data"]
        match operation:
            case "videos":
                self.HarCaptureAddon.decorate_video_data_on_entries(data)
            case "actions":
                self.HarCaptureAddon.add_page_data_to_har({"_actions": data})
            case "page_timings":
                if "title" in data:
                    self.HarCaptureAddon.set_page_title(data["title"])
                    del data["title"]
                self.HarCaptureAddon.add_page_timings_to_har(data)
            case "page_complete":
                logging.info("Page complete")
                self.HarCaptureAddon.add_page_timings_to_har(data)
                self.HarCaptureAddon.end_page()
                self.HarCaptureAddon.new_page()
            case _:
                logging.info(f"BrowserUpData operation: {operation} unknown")

    def _compute_websocket_accept_value(self, key: str) -> str:
        magic_string = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        combined = key + magic_string
        accept_value = base64.b64encode(
            hashlib.sha1(combined.encode()).digest()
        ).decode("utf-8")
        return accept_value
