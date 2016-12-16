class DisableH2CleartextUpgrade:

    """
    We currently only support HTTP/2 over a TLS connection. Some clients try
    to upgrade a connection from HTTP/1.1 to h2c, so we need to remove those
    headers to avoid protocol errors if one endpoints suddenly starts sending
    HTTP/2 frames.
    """

    def process_flow(self, f):
        if f.request.headers.get('upgrade', '') == 'h2c':
            del f.request.headers['upgrade']
            if 'connection' in f.request.headers:
                del f.request.headers['connection']
            if 'http2-settings' in f.request.headers:
                del f.request.headers['http2-settings']

    # Handlers

    def request(self, f):
        self.process_flow(f)
