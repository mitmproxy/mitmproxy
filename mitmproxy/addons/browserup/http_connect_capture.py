import time

from mitmproxy import ctx

RESOLUTION_FAILED_ERROR_MESSAGE = "Unable to resolve host: "
CONNECTION_FAILED_ERROR_MESSAGE = "Unable to connect to host"
RESPONSE_TIMED_OUT_ERROR_MESSAGE = "Response timed out"

# A list of server seen till now is maintained so we can avoid
# using 'connect' time for entries that use an existing connection.

#SERVERS_SEEN: typing.Set[] = set()
SERVERS_SEEN = {}

class HttpConnectCaptureAddOn:

    def __init__(self):
        self.num = 0
        self.har_dump_addon = None

        self.dns_resolution_started_nanos = 0
        self.dns_resolution_finished_nanos = 0

        self.connection_started_nanos = 0
        self.connection_succeeded_time_nanos = 0

        self.send_started_nanos = 0
        self.send_finished_nanos = 0
        self.response_receive_started_nanos = 0
        self.ssl_handshake_started_nanos = 0
        self.http_connect_timing = None



        # HarBuilder.http_connect_timing

    # TCP Callbacks


    def tcp_resolving_server_address_finished(self, flow):
        if not hasattr(flow.request, 'har_entry'):
            return
        self.populate_dns_timings(flow)
        self.dns_resolution_finished_nanos = self.now_time_nanos()

        if self.dns_resolution_started_nanos > 0:
            self.get_http_connect_timing()[
                'dnsTimeNanos'] = self.dns_resolution_finished_nanos - self.dns_resolution_started_nanos
        else:
            self.get_http_connect_timing()['dnsTimeNanos'] = 0

    def tcp_resolving_server_address_started(self, flow):
        self.dns_resolution_started_nanos = int(round(self.now_time_nanos()))
        self.connection_started_nanos = int(round(self.now_time_nanos()))
        self.proxy_to_server_resolution_started()

    # SSL Callbacks
    def ssl_handshake_started(self, flow):
        self.ssl_handshake_started_nanos = int(round(self.now_time_nanos()))

    # HTTP Callbacks

    def http_connect(self, flow):
        self.http_connect_timing = self.get_http_connect_timing()
        self.har_dump_addon.http_connect_timings[
            flow.client_conn] = self.http_connect_timing

    def http_proxy_to_server_request_started(self, flow):
        self.send_started_nanos = self.now_time_nanos()

    def http_proxy_to_server_request_finished(self, flow):
        self.send_finished_nanos = self.now_time_nanos()
        if self.send_started_nanos > 0:
            self.get_har_entry(flow)['timings'][
                'send'] = self.send_finished_nanos - self.send_started_nanos
        else:
            self.get_har_entry(flow)['timings']['send'] = 0

    def http_server_to_proxy_response_receiving(self, flow):
        self.response_receive_started_nanos = self.now_time_nanos()

    def http_server_to_proxy_response_received(self, flow):
        """"""

    # PROXY Callbacks
    def proxy_to_server_resolution_started(self):
        self.get_http_connect_timing()['blockedTimeNanos'] = 0

    def proxy_to_server_connection_succeeded(self, f):
        self.connection_succeeded_time_nanos = self.now_time_nanos()

        if self.connection_started_nanos > 0:
            self.get_http_connect_timing()[
                'connectTimeNanos'] = self.connection_succeeded_time_nanos - self.connection_started_nanos
        else:
            self.get_http_connect_timing()['connectTimeNanos'] = 0

        if self.ssl_handshake_started_nanos > 0:
            self.get_http_connect_timing()[
                'sslHandshakeTimeNanos'] = self.connection_succeeded_time_nanos - self.ssl_handshake_started_nanos
        else:
            self.get_http_connect_timing()['sslHandshakeTimeNanos'] = 0

    def init_har_entry(self, flow):
        ctx.log.debug("Initializing har entry for flow request: {}".format(str(flow.request)))
        setattr(flow.request, 'har_entry', self.har_dump_addon.generate_har_entry())
        self.har_dump_addon.append_har_entry(flow.request.har_entry)

    def error(self, flow):
        if not hasattr(flow.request, 'har_entry'):
            self.init_har_entry(flow)

        req_host_port = flow.request.host
        if flow.request.port != 80:
            req_host_port = req_host_port + ':' + str(flow.request.port)
        original_error = HttpConnectCaptureAddOn.get_original_exception(flow.error)

        self.har_dump_addon.populate_har_entry_with_default_response(flow)

        if 'Name or service not known' in str(original_error):
            self.proxy_to_server_resolution_failed(flow, req_host_port, original_error)
        elif isinstance(original_error, TcpTimeout):
            self.server_to_proxy_response_timed_out(flow, req_host_port, original_error)
        else:
            self.proxy_to_server_connection_failed(flow, original_error)

    # Populate data

    def populate_dns_timings(self, flow):
        har_entry = self.get_har_entry(flow)
        if self.dns_resolution_started_nanos > 0 and har_entry:
            time_now = self.now_time_nanos()
            dns_nanos = time_now - self.dns_resolution_started_nanos
            har_entry['timings']['dnsNanos'] = dns_nanos

    def populate_timings_for_failed_connect(self, flow):
        har_entry = self.get_har_entry(flow)
        if self.connection_started_nanos > 0:
            connect_nanos = self.now_time_nanos() - self.connection_started_nanos
            har_entry['timings']['connectNanos'] = connect_nanos
        self.populate_dns_timings(flow)

    def populate_server_ip_address(self, flow, original_error):
        if flow.server_conn is not None and flow.server_conn.ip_address is not None:
            self.get_har_entry(flow)['serverIPAddress'] = str(
                flow.server_conn.ip_address[0])

    def populate_connect_and_ssl_timings(self, flow):
        ssl_time = -1
        connect_time = -1

        # if flow.server_conn and flow.server_conn not in SERVERS_SEEN:
        connect_time = (flow.server_conn.timestamp_tcp_setup -
                        flow.server_conn.timestamp_start)
        connect_time = self.timestamp_to_nanos(connect_time)

        if flow.server_conn.timestamp_tls_setup is not None:
            ssl_time = (flow.server_conn.timestamp_tls_setup -
                        flow.server_conn.timestamp_tcp_setup)
            ssl_time = self.timestamp_to_nanos(ssl_time)

           # SERVERS_SEEN.add(flow.server_conn)
        har_entry = self.get_har_entry(flow)
        har_entry['timings']['sslNanos'] = ssl_time
        har_entry['timings']['connectNanos'] = connect_time

    def proxy_to_server_resolution_failed(self, flow, req_host_port, original_error):
        msg = RESOLUTION_FAILED_ERROR_MESSAGE + req_host_port
        self.create_har_entry_for_failed_connect(flow, msg)
        self.populate_dns_timings(flow)
        self.populate_server_ip_address(flow, original_error)

        self.get_har_entry(flow)['time'] = self.calculate_total_elapsed_time(flow)

    def proxy_to_server_connection_failed(self, flow, original_error):
        msg = CONNECTION_FAILED_ERROR_MESSAGE
        self.create_har_entry_for_failed_connect(flow, msg)
        self.populate_timings_for_failed_connect(flow)
        self.populate_server_ip_address(flow, original_error)

        self.get_har_entry(flow)['time'] = self.calculate_total_elapsed_time(flow)

    def server_to_proxy_response_timed_out(self, flow, req_host_port, original_error):
        msg = RESPONSE_TIMED_OUT_ERROR_MESSAGE
        self.create_har_entry_for_failed_connect(flow, msg)
        self.populate_timings_for_failed_connect(flow)
        self.populate_server_ip_address(flow, original_error)
        self.populate_connect_and_ssl_timings(flow)

        current_time_nanos = self.now_time_nanos()

        har_entry = self.get_har_entry(flow)

        if self.send_started_nanos > 0 and self.send_finished_nanos == 0:
            har_entry['timings']['sendNanos'] = current_time_nanos - self.send_started_nanos

        elif self.send_finished_nanos > 0 and self.response_receive_started_nanos == 0:
            har_entry['timings']['waitNanos'] = current_time_nanos - self.send_finished_nanos

        elif self.response_receive_started_nanos > 0:
            har_entry['timings']['receiveNanos'] = current_time_nanos - self.response_receive_started_nanos

        har_entry['time'] = self.calculate_total_elapsed_time(flow)

    def create_har_entry_for_failed_connect(self, flow, msg):
        har_entry = self.get_har_entry(flow)
        har_entry['response']['_errorMessage'] = msg

    def calculate_total_elapsed_time(self, flow):
        timings = self.get_har_entry(flow)['timings']
        result = (0 if timings.get('blockedNanos', -1) == -1 else timings['blockedNanos']) + \
                 (0 if timings.get('dnsNanos', -1) == -1 else timings['dnsNanos']) + \
                 (0 if timings.get('connectNanos', -1) == -1 else timings['connectNanos']) + \
                 (0 if timings.get('sendNanos', -1) == -1 else timings['sendNanos']) + \
                 (0 if timings.get('waitNanos', -1) == -1 else timings['waitNanos']) + \
                 (0 if timings.get('receiveNanos', -1) == -1 else timings['receiveNanos'])
        return self.nano_to_ms(result)

    def get_har_entry(self, flow):
        return flow.request.har_entry

    def get_http_connect_timing(self):
        if self.http_connect_timing is None:
            self.http_connect_timing = self.generate_http_connect_timing()
        return self.http_connect_timing

    @staticmethod
    def get_original_exception(flow_error):
        result = flow_error.cause
        while True:
            if hasattr(result, '__cause__') and result.__cause__:
                result = result.__cause__
            else:
                break
        return result

    @staticmethod
    def now_time_nanos():
        return int(round(time.time() * 1000000000))

    @staticmethod
    def timestamp_to_nanos(timestamp):
        return int(round(timestamp * 1000000000))

    @staticmethod
    def nano_to_ms(time_nano):
        return int(time_nano / 1000000)

addons = [
    HttpConnectCaptureAddOn()
]