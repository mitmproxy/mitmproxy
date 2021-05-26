import base64
import typing

from mitmproxy import connection
from mitmproxy.utils import strutils
from mitmproxy.addons.browserup.har.har_builder import HarBuilder
from mitmproxy.addons.browserup.har.har_capture_types import HarCaptureTypes
from datetime import datetime
from datetime import timezone
from mitmproxy import ctx

# all the specifics to do with converting a flow into a HAR
# A list of server seen till now is maintained so we can avoid
# using 'connect' time for entries that use an existing connection.
SERVERS_SEEN: typing.Set[connection.Server] = set()

DEFAULT_PAGE_REF = "Default"
DEFAULT_PAGE_TITLE = "Default"
REQUEST_SUBMITTED_FLAG = "_request_submitted"


class FlowCaptureMixin(object):

    def capture_request(self, flow):
        full_url = self.get_full_url(flow.request)
        ctx.log.debug('Populating har entry for request: {}'.format(full_url))

        har_entry = flow.get_har_entry()
        har_entry['pageref'] = self.get_current_page_ref()
        har_entry['startedDateTime'] = datetime.fromtimestamp(flow.request.timestamp_start, timezone.utc).isoformat()
        har_request = HarBuilder.entry_request()
        har_request['method'] = flow.request.method
        har_request['url'] = full_url
        har_request['httpVersion'] = flow.request.http_version
        har_request['queryString'] = self.name_value(flow.request.query or {})
        har_request['headersSize'] = len(str(flow.request.headers))

        har_request['_updated'] = datetime.fromtimestamp(flow.request.timestamp_start, timezone.utc).isoformat()

        har_entry['request'] = har_request
        req_url = 'none'
        if flow.request is not None:
            req_url = flow.request.url

        ctx.log.debug('Incoming request, url: {}'.format(req_url))

        if HarCaptureTypes.REQUEST_COOKIES in self.har_capture_types:
            har_entry['request']['cookies'] = self.format_request_cookies(flow.request.cookies.fields)

        if HarCaptureTypes.REQUEST_HEADERS in self.har_capture_types:
            har_entry['request']['headers'] = self.name_value(flow.request.headers)

        if HarCaptureTypes.REQUEST_CONTENT in self.har_capture_types:
            params = [
                {"name": a, "value": b}
                for a, b in flow.request.urlencoded_form.items(multi=True)
            ]
            har_entry["request"]["postData"] = {
                "mimeType": flow.request.headers.get("Content-Type", ""),
                "text": flow.request.get_text(strict=False),
                "params": params
            }

        har_entry['request']['bodySize'] = len(flow.request.raw_content) if flow.request.raw_content else 0
        flow.set_har_entry(har_entry)

    def capture_response(self, flow):
        ctx.log.debug('Incoming response for request to url: {}'.format(flow.request.url))

        t = HarBuilder.entry_timings()
        t['send'] = self.diff_millis(flow.request.timestamp_end, flow.request.timestamp_start)
        t['wait'] = self.diff_millis(flow.request.timestamp_end, flow.response.timestamp_start)
        t['receive'] = self.diff_millis(flow.response.timestamp_end, flow.response.timestamp_start)

        if flow.server_conn and flow.server_conn not in SERVERS_SEEN:
            t['connect'] = self.diff_millis(flow.server_conn.timestamp_tcp_setup, flow.server_conn.timestamp_start)

            if flow.server_conn.timestamp_tls_setup is not None:
                t['ssl'] = self.diff_millis(flow.server_conn.timestamp_tls_setup, flow.server_conn.timestamp_tcp_setup)

            SERVERS_SEEN.add(flow.server_conn)

        full_time = sum(v for v in t.values() if v > -1)

        har_entry = flow.get_har_entry()
        har_entry['timings'] = t

        # Response body size and encoding
        response_body_size = len(flow.response.raw_content) if flow.response.raw_content else 0
        response_body_decoded_size = len(
            flow.response.content) if flow.response.content else 0
        response_body_compression = response_body_decoded_size - response_body_size

        har_response = HarBuilder.entry_response()
        har_response["status"] = flow.response.status_code
        har_response["statusText"] = flow.response.reason
        har_response["httpVersion"] = flow.response.http_version

        if HarCaptureTypes.RESPONSE_COOKIES in self.har_capture_types:
            har_response["cookies"] = \
                self.format_response_cookies(flow.response.cookies.fields)

        if HarCaptureTypes.RESPONSE_HEADERS in self.har_capture_types:
            har_response["headers"] = self.name_value(flow.response.headers)

        if flow.response.status_code in [300, 301, 302, 303, 307]:
            har_response['redirectURL'] = flow.response.headers['Location']

        content = har_response['content']
        content['size'] = response_body_size
        content['compression'] = response_body_compression
        content['mimeType'] = flow.response.headers.get('Content-Type', '')

        if HarCaptureTypes.RESPONSE_CONTENT in self.har_capture_types:
            if strutils.is_mostly_bin(flow.response.content):
                if HarCaptureTypes.RESPONSE_BINARY_CONTENT in self.har_capture_types:
                    har_response["content"]["text"] = base64.b64encode(flow.response.content).decode()
                    har_response["content"]["encoding"] = "base64"
            else:
                har_response["content"]["text"] = flow.response.get_text(strict=False )

        har_response["redirectURL"] = flow.response.headers.get('Location', '')
        har_response["headersSize"] = len(str(flow.response.headers))
        har_response["bodySize"] = response_body_size

        har_entry['response'] = har_response
        har_entry['time'] = full_time
        har_entry['pageref'] = self.get_current_page_ref()

        har_entry['timings'] = t

        if flow.server_conn.connected:
            har_entry["serverIPAddress"] = str(
                flow.server_conn.ip_address[0])

        flow.set_har_entry(har_entry)
        ctx.log.debug('Populated har entry for response: {}, entry: {}'.format(flow.request.url, str(har_entry)))

    def capture_websocket_message(self, flow):
        if HarCaptureTypes.WEBSOCKET_MESSAGES in self.har_capture_types:
            har_entry = flow.get_har_entry()
            msg = flow.websocket.messages[-1]

            data = msg.content
            try:
                data = data.decode("utf-8")
            except (UnicodeDecodeError, AttributeError):
                pass

            har_entry.setdefault("_webSocketMessages", []).append({
                "type": 'send' if msg.from_client else 'receive',
                "opcode": msg.type.value,
                "data": data,
                "time": msg.timestamp
            })
            flow.set_har_entry(har_entry)

    # Capture errors as messages like Chrome har export does
    def capture_websocket_error(self, flow):
        if HarCaptureTypes.WEBSOCKET_MESSAGES in self.har_capture_types:
            har_entry = flow.get_har_entry()
            har_entry.setdefault("_webSocketMessages", []).append({
                "type": 'error',
                "time": flow.error.timestamp,
                "opcode": -1,
                "data": flow.error.msg
            })
        flow.set_har_entry(har_entry)

    # for all of these:  Use -1 if the timing does not apply to the current request.
    # Time required to create TCP connection.

    # question: how to make the server connect time stop reporting once it has happened.
    #
    # connection id seems like it is unique. We can choose to only report it once.
    # we could also put it on the page object.

    def get_full_url(self, request):
        host_port = request.host
        if request.method == 'CONNECT':
            if request.port != 443:
                host_port = host_port + ':' + str(request.port)
            host_port = 'https://' + host_port
        else:
            if request.scheme is not None:
                host_port = request.url
            else:
                host_port = host_port + ":" + str(request.port)

        return host_port

    def diff_millis(self, ts_end, ts_start):
        if ts_end is None or ts_start is None:
            return -1
        else:
            return round((ts_end - ts_start) * 1000)
