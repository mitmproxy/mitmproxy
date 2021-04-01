import mitmproxy


class DisableH2C:

    """
    We currently only support HTTP/2 over a TLS connection.

    Some clients try to upgrade a connection from HTTP/1.1 to h2c. We need to
    remove those headers to avoid protocol errors if one endpoints suddenly
    starts sending HTTP/2 frames.

    Some clients might use HTTP/2 Prior Knowledge to directly initiate a session
    by sending the connection preface. We just kill those flows.
    """

    def process_flow(self, f):
        if f.request.headers.get('upgrade', '') == 'h2c':
            mitmproxy.ctx.log.warn("HTTP/2 cleartext connections (h2c upgrade requests) are currently not supported.")
            del f.request.headers['upgrade']
            if 'connection' in f.request.headers:
                del f.request.headers['connection']
            if 'http2-settings' in f.request.headers:
                del f.request.headers['http2-settings']

        is_connection_preface = (
            f.request.method == 'PRI' and
            f.request.path == '*' and
            f.request.http_version == 'HTTP/2.0'
        )
        if is_connection_preface:
            f.kill()
            mitmproxy.ctx.log.warn("Initiating HTTP/2 connections with prior knowledge are currently not supported.")

    # Handlers

    def request(self, f):
        self.process_flow(f)
