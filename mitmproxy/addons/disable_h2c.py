import logging


class DisableH2C:
    """
    Disable unsupported h2c cleartext mechanisms.

    The HTTP/1.1 ``Upgrade: h2c`` mechanism is never supported: those headers
    are stripped to prevent protocol errors.

    When the ``http2`` option is disabled, h2c prior knowledge connections
    (``PRI * HTTP/2.0``) fall through to the HTTP/1.1 parser and are killed
    here to avoid forwarding nonsensical requests upstream.
    """

    def process_flow(self, f):
        if f.request.headers.get("upgrade", "") == "h2c":
            logging.warning(
                "HTTP/2 cleartext upgrade requests (Upgrade: h2c) are not supported."
            )
            del f.request.headers["upgrade"]
            if "connection" in f.request.headers:
                del f.request.headers["connection"]
            if "http2-settings" in f.request.headers:
                del f.request.headers["http2-settings"]

        is_connection_preface = (
            f.request.method == "PRI"
            and f.request.path == "*"
            and f.request.http_version == "HTTP/2.0"
        )
        if is_connection_preface:
            if f.killable:
                f.kill()
            logging.warning(
                "HTTP/2 cleartext connections with prior knowledge are not supported "
                "when the http2 option is disabled."
            )

    # Handlers

    def request(self, f):
        self.process_flow(f)
