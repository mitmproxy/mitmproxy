import json
import base64
import typing
import tempfile

from datetime import datetime
from datetime import timezone
import dateutil.parser

import copy

import asyncio

from mitmproxy import ctx

from enum import Enum, auto

import falcon

from mitmproxy import connection
from mitmproxy.utils import strutils
from mitmproxy.net.http import cookies

# A list of server seen till now is maintained so we can avoid
# using 'connect' time for entries that use an existing connection.
SERVERS_SEEN = set()


DEFAULT_PAGE_REF = "Default"
DEFAULT_PAGE_TITLE = "Default"

REQUEST_SUBMITTED_FLAG = "_request_submitted"

class HarCaptureTypes(Enum):
    REQUEST_HEADERS = auto()
    REQUEST_COOKIES = auto()
    REQUEST_CONTENT = auto()
    REQUEST_BINARY_CONTENT = auto()
    RESPONSE_HEADERS = auto()
    RESPONSE_COOKIES = auto()
    RESPONSE_CONTENT = auto()
    RESPONSE_BINARY_CONTENT = auto()

    WEBSOCKET_MESSAGES = auto()


    REQUEST_CAPTURE_TYPES = {
        REQUEST_HEADERS,
        REQUEST_CONTENT,
        REQUEST_BINARY_CONTENT,
        REQUEST_COOKIES}

    RESPONSE_CAPTURE_TYPES = {
        RESPONSE_HEADERS,
        RESPONSE_CONTENT,
        RESPONSE_BINARY_CONTENT,
        RESPONSE_COOKIES}

    HEADER_CAPTURE_TYPES = {
        REQUEST_HEADERS,
        RESPONSE_HEADERS}

    NON_BINARY_CONTENT_CAPTURE_TYPES = {
        REQUEST_CONTENT,
        RESPONSE_CONTENT}

    BINARY_CONTENT_CAPTURE_TYPES = {
        REQUEST_BINARY_CONTENT,
        RESPONSE_BINARY_CONTENT}

    ALL_CONTENT_CAPTURE_TYPES = {
        REQUEST_CONTENT, RESPONSE_CONTENT,
        REQUEST_BINARY_CONTENT,
        RESPONSE_BINARY_CONTENT}

    COOKIE_CAPTURE_TYPES = {
        REQUEST_COOKIES,
        RESPONSE_COOKIES}


class HarDumpAddonResource:

    def addon_path(self):
        return "har"

    def __init__(self, harDumpAddOn):
        self.name = "hardump"
        self.harDumpAddOn = harDumpAddOn

    def on_get(self, req, resp, method_name):
        try:
            asyncio.get_event_loop()
        except:
            asyncio.set_event_loop(asyncio.new_event_loop())
        getattr(self, "on_" + method_name)(req, resp)

    def on_get_har(self, req, resp):
        clean_har = req.get_param('cleanHar') == 'true'
        har = self.harDumpAddOn.get_har(clean_har)

        filtered_har = self.harDumpAddOn.filter_har_for_report(har)

        har_file = self.harDumpAddOn.save_har(filtered_har)

        if clean_har:
            self.harDumpAddOn.mark_har_entries_submitted(har)

        resp.status = falcon.HTTP_200
        resp.content_type = falcon.MEDIA_JSON
        resp.body = json.dumps({
            "path": har_file.name,
            "json": filtered_har
        }, ensure_ascii=False)

    def on_new_har(self, req, resp):
        page_ref = req.get_param('pageRef')
        page_title = req.get_param('pageTitle')

        har = self.harDumpAddOn.new_har(page_ref, page_title, True)

        har_file = self.harDumpAddOn.save_har(har)

        resp.status = falcon.HTTP_200
        resp.body = json.dumps({
            "path": har_file.name,
            "json": har
        }, ensure_ascii=False)

    def on_end_har(self, req, resp):
        har = self.harDumpAddOn.end_har()

        har_file = self.harDumpAddOn.save_har(har)

        resp.status = falcon.HTTP_200
        resp.body = json.dumps({
            "path": har_file.name,
            "json": har
        }, ensure_ascii=False)

    def on_new_page(self, req, resp):
        page_ref = req.get_param('pageRef')
        page_title = req.get_param('pageTitle')

        har = self.harDumpAddOn.new_page(page_ref, page_title)

        har_file = self.harDumpAddOn.save_har(har)

        resp.status = falcon.HTTP_200
        resp.body = json.dumps({
            "path": har_file.name,
            "json": har
        }, ensure_ascii=False)

    def on_end_page(self, req, resp):
        har = self.harDumpAddOn.end_page()

        har_file = self.harDumpAddOn.save_har(har)

        resp.status = falcon.HTTP_200
        resp.body = json.dumps({
            "path": har_file.name,
            "json": har
        }, ensure_ascii=False)

    def on_set_har_capture_types(self, req, resp):
        capture_types = req.get_param('captureTypes')
        capture_types = capture_types.strip("[]").split(",")

        capture_types_parsed = []
        for ct in capture_types:
            ct = ct.strip(" ")
            if ct == "":
                break

            if not hasattr(HarCaptureTypes, ct):
                resp.status = falcon.HTTP_400
                resp.body = "Invalid HAR Capture type"
                return

            capture_types_parsed.append(HarCaptureTypes[ct])

        self.harDumpAddOn.har_capture_types = capture_types_parsed
        resp.status = falcon.HTTP_200


class HarDumpAddOn:

    def __init__(self):
        self.num = 0
        self.har = None
        self.har_page_count = 0
        self.har_capture_types = []
        self.current_har_page = None
        self.dns_resolution_started_nanos = 0
        self.connection_started_nanos = 0
        self.send_started_nanos = 0
        self.send_finished_nanos = 0
        self.response_receive_started_nanos = 0
        self.http_connect_timings = {}

    def get_har_entry(self, flow):
        return flow.request.har_entry

    def is_har_entry_submitted(self, har_entry):
        return REQUEST_SUBMITTED_FLAG in har_entry

    def har_entry_has_response(self, har_entry):
        return bool(har_entry['response'])

    def har_entry_clear_request(self, har_entry):
        har_entry['request'] = {}

    def filter_har_for_report(self, har):
        if har is None:
            return har

        har_copy = copy.deepcopy(har)
        entries_to_report = []
        for entry in har_copy['log']['entries']:
            if self.is_har_entry_submitted(entry):
                if self.har_entry_has_response(entry):
                    del entry[REQUEST_SUBMITTED_FLAG]
                    self.har_entry_clear_request(entry)
                    entries_to_report.append(entry)
            else:
                entries_to_report.append(entry)
        har_copy['log']['entries'] = entries_to_report

        return har_copy

    def mark_har_entries_submitted(self, har):
        if har is not None:
            for entry in har['log']['entries']:
                entry[REQUEST_SUBMITTED_FLAG] = True

    def get_har(self, clean_har):
        if clean_har:
            return self.new_har(DEFAULT_PAGE_REF, DEFAULT_PAGE_TITLE)
        return self.har

    def get_default_har_page(self):
        for hp in self.har['log']['pages']:
            if hp['title'] == DEFAULT_PAGE_TITLE:
                return hp
        return None


    def generate_new_har_log(self):
        return {
            "version": "1.1",
            "creator": {
                "name": "BrowserUp Proxy",
                "version": "0.1",
                "comment": ""
            },
            "entries": [],
            "pages": []
        }

    def generate_new_har(self):
        return {
            "log": self.generate_new_har_log()
        }

    def generate_new_page_timings(self):
        return {
            "onContentLoad": 0,
            "onLoad": 0,
            "comment": ""
        }

    def generate_new_har_page(self):
        return {
            "title": "",
            "id": "",
            "startedDateTime": "",
            "pageTimings": self.generate_new_page_timings()
        }

    def generate_new_har_post_data(self):
        return {
            "mimeType": "multipart/form-data",
            "params": [],
            "text": "plain posted data",
            "comment": ""
        }

    def generate_har_entry_request(self):
        return {
            "method": "",
            "url": "",
            "httpVersion": "",
            "cookies": [],
            "headers": [],
            "queryString": [],
            "headersSize": 0,
            "bodySize": 0,
            "comment": "",
            "additional": {}
        }

    def generate_har_timings(self):
        return {
            "blockedNanos": -1,
            "dnsNanos": -1,
            "connectNanos": -1,
            "sslNanos": -1,
            "sendNanos": 0,
            "waitNanos": 0,
            "receiveNanos": 0,
            "comment": ""
        }

    def generate_har_entry_response(self):
        return {
            "status": 0,
            "statusText": "",
            "httpVersion": "",
            "cookies": [],
            "headers": [],
            "content": {
                "size": 0,
                "compression": 0,
                "mimeType": "",
                "text": "",
                "encoding": "",
                "comment": "",
            },
            "redirectURL": "",
            "headersSize": -1,
            "bodySize": -1,
            "comment": 0,
        }

    def generate_har_entry_response_for_failure(self):
        result = self.generate_har_entry_response()
        result['status'] = 0
        result['statusText'] = ""
        result['httpVersion'] = "unknown"
        result['_errorMessage'] = "No response received"
        return result

    def generate_har_entry(self):
        return {
            "pageref": "",
            "startedDateTime": "",
            "time": 0,
            "request": {},
            "response": {},
            "cache": {},
            "timings": self.generate_har_timings(),
            "serverIPAddress": "",
            "connection": "",
            "comment": ""
        }

    def get_or_create_har(self, page_ref, page_title, create_page=False):
        if self.har is None:
            self.new_har(page_ref, page_title, create_page)
        return self.har

    def new_page(self, page_ref, page_title):
        ctx.log.info(
            'Creating new page with initial page ref: {}, title: {}'.
                format(page_ref, page_title))

        har = self.get_or_create_har(page_ref, page_title, False)

        end_of_page_har = None

        if self.current_har_page is not None:
            current_page_ref = self.current_har_page['id']

            self.end_page()

            end_of_page_har = self.copy_har_through_page_ref(har,
                                                             current_page_ref)

        if page_ref is None:
            self.har_page_count += 1
            page_ref = "Page " + str(self.har_page_count)

        if page_title is None:
            page_title = page_ref

        new_page = self.generate_new_har_page()
        new_page['title'] = page_title
        new_page['id'] = page_ref
        new_page['startedDateTime'] = datetime.utcnow().isoformat()
        har['log']['pages'].append(new_page)

        self.current_har_page = new_page

        return end_of_page_har

    def copy_har_through_page_ref(self, har, page_ref):
        if har is None:
            return None

        if har['log'] is None:
            return self.generate_new_har()

        page_refs_to_copy = []

        for page in har['log']['pages']:
            page_refs_to_copy.append(page['id'])
            if page_ref == page['id']:
                break

        log_copy = self.generate_new_har_log()

        for entry in har['log']['entries']:
            if entry['pageref'] in page_refs_to_copy:
                log_copy['entries'].append(entry)

        for page in har['log']['pages']:
            if page['id'] in page_refs_to_copy:
                log_copy['pages'].append(page)

        har_copy = self.generate_new_har()
        har_copy['log'] = log_copy

        return har_copy

    def get_current_page_ref(self):
        har_page = self.current_har_page
        if har_page is None:
            har_page = self.get_or_create_default_page()
        return har_page['id']

    def get_or_create_default_page(self):
        default_page = self.get_default_page()
        if default_page is None:
            default_page = self.add_default_page()
        return default_page

    def add_default_page(self):
        self.get_or_create_har(DEFAULT_PAGE_REF, DEFAULT_PAGE_TITLE, False)
        new_page = self.generate_new_har_page()
        new_page['title'] = DEFAULT_PAGE_REF
        new_page['startedDateTime'] = datetime.utcnow().isoformat()
        new_page['id'] = DEFAULT_PAGE_REF
        self.har['log']['pages'].append(new_page)
        return new_page

    def get_default_page(self):
        for p in self.har['log']['pages']:
            if p['id'] == DEFAULT_PAGE_REF:
                return p
        return None

    def new_har(self, initial_page_ref, initial_page_title, create_page=False):
        if create_page:
            ctx.log.info(
                'Creating new har with initial page ref: {}, title: {}'.
                    format(initial_page_ref, initial_page_title))
        else:
            ctx.log.info('Creating new har without initial page')

        old_har = self.end_har()

        self.har_page_count = 0

        self.har = self.generate_new_har()

        if create_page:
            self.new_page(initial_page_ref, initial_page_title)

        self.copy_entries_without_response(old_har)

        return old_har

    def copy_entries_without_response(self, old_har):
        if old_har is not None:
            for entry in old_har['log']['entries']:
                if not self.har_entry_has_response(entry):
                    self.har['log']['entries'].append(entry)

    def end_har(self):
        ctx.log.info('Ending current har...')

        old_har = self.har
        if old_har is None: return

        self.end_page()

        self.har = None

        return old_har

    def end_page(self):
        ctx.log.info('Ending current page...')

        previous_har_page = self.current_har_page
        self.current_har_page = None

        if previous_har_page is None:
            return

        if 'startedDateTime' in previous_har_page:
            on_load_delta_ms = (datetime.utcnow() - dateutil.parser.isoparse(
                previous_har_page['startedDateTime'])).total_seconds() * 1000
            previous_har_page['pageTimings']['onLoad'] = int(on_load_delta_ms)

        default_har_page = self.get_default_har_page()
        if default_har_page is not None:
            if 'startedDateTime' in default_har_page:
                default_har_page['pageTimings']['onLoad'] = \
                    (
                            datetime.utcnow() - dateutil.parser.isoparse(
                        default_har_page['startedDateTime'])
                    ).total_seconds() * 1000

    def add_har_page(self, pageRef, pageTitle):
        ctx.log.debug('Adding har page with ref: {} and title: {}'.format(pageRef, pageTitle))

        har_page = {
            "id": pageRef,
            "title:": pageTitle,
            "startedDateTime": datetime.utcnow().isoformat(),
            "pageTimings": {
                "onContentLoad": 0,
                "onLoad": 0,
                "comment": ""
            }
        }
        self.har['log']['pages'].append(har_page)
        return har_page

    def get_resource(self):
        return HarDumpAddonResource(self)

    def save_har(self, har):
        json_dump: str = json.dumps(har, indent=2)

        tmp_file = tempfile.NamedTemporaryFile(mode="wb", prefix="har_dump_",
                                               delete=False)

        raw: bytes = json_dump.encode()

        tmp_file.write(raw)
        tmp_file.flush()
        tmp_file.close()

        return tmp_file

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

    def consume_http_connect_timing(self, client_conn):
        if client_conn in self.http_connect_timings:
            return self.http_connect_timings.pop(client_conn, None)
        return None

    def populate_har_entry_with_default_response(self, flow):
        full_url = self.get_full_url(flow.request)

        ctx.log.debug('Populating har entry for request: {}'.format(full_url))

        har_entry = self.get_har_entry(flow)

        har_entry['pageref'] = self.get_current_page_ref()
        har_entry['startedDateTime'] = datetime.fromtimestamp(flow.request.timestamp_start, timezone.utc).isoformat()
        har_request = self.generate_har_entry_request()
        har_request['method'] = flow.request.method
        har_request['url'] = full_url
        har_request['httpVersion'] = flow.request.http_version
        har_request['queryString'] = self.name_value(flow.request.query or {})
        har_request['headersSize'] = len(str(flow.request.headers))

        har_entry['request'] = har_request

    def append_har_entry(self, har_entry):
        har = self.get_or_create_har(DEFAULT_PAGE_REF, DEFAULT_PAGE_TITLE, True)
        har['log']['entries'].append(har_entry)

    def request(self, flow):
        if 'WhiteListFiltered' in flow.metadata or 'BlackListFiltered' in flow.metadata:
            return
        print("request called in addon {}".format(self.__class__.__name__))

        har_entry = self.get_har_entry(flow)

        self.populate_har_entry_with_default_response(flow)

        req_url = 'none'
        if flow.request is not None:
            req_url = flow.request.url

        ctx.log.debug('Incoming request, url: {}'.format(req_url))

        self.get_or_create_har(DEFAULT_PAGE_REF, DEFAULT_PAGE_TITLE, True)

        if HarCaptureTypes.REQUEST_COOKIES in self.har_capture_types:
            self.capture_request_cookies(flow)

        if HarCaptureTypes.REQUEST_HEADERS in self.har_capture_types:
            self.capture_request_headers(flow)

        if HarCaptureTypes.RESPONSE_CONTENT in self.har_capture_types:
            self.capture_request_content(flow)

        har_entry['request']['bodySize'] = \
            len(flow.request.raw_content) if flow.request.raw_content else 0

        connect_timing = self.consume_http_connect_timing(flow)
        if connect_timing is not None:
            har_entry['timings']['sslNanos'] = connect_timing['sslHandshakeTimeNanos']
            har_entry['timings']['connectNanos'] = connect_timing['connectTimeNanos']
            har_entry['timings']['blockedNanos'] = connect_timing['blockedTimeNanos']
            har_entry['timings']['dnsNanos'] = connect_timing['dnsTimeNanos']


    def capture_request_cookies(self, flow):
        har_entry = self.get_har_entry(flow)
        har_entry['request']['cookies'] = \
            self.format_request_cookies(flow.request.cookies.fields)

    def capture_request_headers(self, flow):
        har_entry = self.get_har_entry(flow)
        har_entry['request']['headers'] = \
            self.name_value(flow.request.headers)

    def capture_request_content(self, flow):
        har_entry = self.get_har_entry(flow)
        params = [
            {"name": a, "value": b}
            for a, b in flow.request.urlencoded_form.items(multi=True)
        ]
        har_entry["request"]["postData"] = {
            "mimeType": flow.request.headers.get("Content-Type", ""),
            "text": flow.request.get_text(strict=False),
            "params": params
        }

    def capture_websocket_message(self, flow):
        har_entry = self.get_har_entry(flow.handshake_flow)
        msg = flow.messages[-1]
        har_entry.setdefault("_webSocketMessages", []).append({
            "type": 'send' if msg.from_client else 'receive',
            "opcode": msg.type.value,
            "data": msg.content,
            "time": msg.timestamp
        })

    # Capture errors as messages like Chrome har export does
    def capture_websocket_error(self, flow):
        har_entry = self.get_har_entry(flow.handshake_flow)
        har_entry.setdefault("_webSocketMessages", []).append({
            "type": 'error',
            "time": flow.error.timestamp,
            "opcode": -1,
            "data": flow.error.msg
        })

    def websocket_message(self, flow):
        self.capture_websocket_message(flow)

    def websocket_error(self, flow):
        self.capture_websocket_error(flow)

    def response(self, flow):
        har_entry = self.get_har_entry(flow)

        ctx.log.debug('Incoming response for request to url: {}'.format(flow.request.url))

        if 'WhiteListFiltered' in flow.metadata or 'BlackListFiltered' in flow.metadata:
            ctx.log.debug('Black/White list filtered, return nothing.')
            return

        # -1 indicates that these values do not apply to current request
        self.get_or_create_har(DEFAULT_PAGE_REF, DEFAULT_PAGE_TITLE, True)

        ssl_time = -1
        connect_time = -1

        if flow.server_conn and flow.server_conn not in SERVERS_SEEN:
            connect_time = (flow.server_conn.timestamp_tcp_setup -
                            flow.server_conn.timestamp_start)

            if flow.server_conn.timestamp_tls_setup is not None:
                ssl_time = (flow.server_conn.timestamp_tls_setup -
                            flow.server_conn.timestamp_tcp_setup)

            SERVERS_SEEN.add(flow.server_conn)

        timings = self.calculate_timings(connect_time, flow, ssl_time)
        timings['dnsNanos'] = int(har_entry['timings']['dnsNanos'])

        full_time = sum(v for v in timings.values() if v > -1)

        # Response body size and encoding
        response_body_size = len(
            flow.response.raw_content) if flow.response.raw_content else 0
        response_body_decoded_size = len(
            flow.response.content) if flow.response.content else 0
        response_body_compression = response_body_decoded_size - response_body_size

        har_response = self.generate_har_entry_response()
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
                    har_response["content"]["text"] = base64.b64encode(
                        flow.response.content).decode()
                    har_response["content"]["encoding"] = "base64"
            else:
                har_response["content"]["text"] = flow.response.get_text(
                    strict=False)

        har_response["redirectURL"] = flow.response.headers.get('Location', '')
        har_response["headersSize"] = len(str(flow.response.headers))
        har_response["bodySize"] = response_body_size

        har_entry['response'] = har_response
        har_entry['time'] = self.nano_to_ms(full_time)
        har_entry['pageref'] = self.get_current_page_ref()

        har_entry['timings'] = timings

        if flow.server_conn.connected:
            har_entry["serverIPAddress"] = str(
                flow.server_conn.ip_address[0])

        ctx.log.debug('Populated har entry for response: {}, entry: {}'.format(flow.request.url, str(har_entry)))


    def calculate_timings(self, connect_time, flow, ssl_time):
        timings_raw = {
            'sendNanos': flow.request.timestamp_end - flow.request.timestamp_start,
            'receiveNanos': flow.response.timestamp_end - flow.response.timestamp_start,
            'waitNanos': flow.response.timestamp_start - flow.request.timestamp_end,
            'connectNanos': connect_time,
            'sslNanos': ssl_time,
        }
        # HAR timings are integers in ms, so we re-encode the raw timings to that format.
        # In HAR Timings parser we expect input metrics in Nanos
        return {
            k: int(self.sec_to_nano(v)) if v != -1 else -1
            for k, v in timings_raw.items()
        }

    def format_cookies(self, cookie_list):
        rv = []

        for name, value, attrs in cookie_list:
            cookie_har = {
                "name": name,
                "value": value,
            }

            # HAR only needs some attributes
            for key in ["path", "domain", "comment"]:
                if key in attrs:
                    cookie_har[key] = attrs[key]

            # These keys need to be boolean!
            for key in ["httpOnly", "secure"]:
                cookie_har[key] = bool(key in attrs)

            # Expiration time needs to be formatted
            expire_ts = cookies.get_expiration_ts(attrs)
            if expire_ts is not None:
                cookie_har["expires"] = datetime.fromtimestamp(expire_ts,
                                                               timezone.utc).isoformat()

            rv.append(cookie_har)

        return rv

    def format_request_cookies(self, fields):
        return self.format_cookies(cookies.group_cookies(fields))

    def format_response_cookies(self, fields):
        return self.format_cookies((c[0], c[1][0], c[1][1]) for c in fields)

    def name_value(self, obj):
        """
            Convert (key, value) pairs to HAR format.
        """
        return [{"name": k, "value": v} for k, v in obj.items()]

    @staticmethod
    def nano_to_ms(time_nano):
        return int(time_nano / 1000000)

    @staticmethod
    def sec_to_nano(time_sec):
        return int(time_sec * 1000000000)

addons = [
    HarDumpAddOn()
]