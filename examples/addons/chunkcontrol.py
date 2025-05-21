"""Do not add CRLF when setting x-manual-chunk in chunked transfer-encoding."""

from mitmproxy import http
from mitmproxy.proxy.layers.http import _http1

# Save the original send methods
original_http1_server_send = _http1.Http1Server.send
original_http1_client_send = _http1.Http1Client.send


def new_http1_server_send(self, event):
    # Handle ResponseData events
    if isinstance(event, _http1.ResponseData):
        response = self.response
        if getattr(response, 'manual_chunk', False):
            # Send raw data without chunk formatting
            if event.data:
                yield _http1.commands.SendData(self.conn, event.data)
            return
    # Handle ResponseEndOfMessage events
    elif isinstance(event, _http1.ResponseEndOfMessage):
        response = self.response
        manual_chunk = getattr(response, 'manual_chunk', False)
        if (
            self.request.method.upper() != "HEAD"
            and "chunked" in response.headers.get("transfer-encoding", "").lower()
            and not manual_chunk  # Only send terminator if not manual_chunk
        ):
            yield _http1.commands.SendData(self.conn, b"0\r\n\r\n")
        yield from self.mark_done(response=True)
        return
    # Proceed with original behavior for other events
    yield from original_http1_server_send(self, event)


def new_http1_client_send(self, event):
    # Handle RequestData events
    if isinstance(event, _http1.RequestData):
        request = self.request
        if getattr(request, 'manual_chunk', False):
            # Send raw data without chunk formatting
            if event.data:
                yield _http1.commands.SendData(self.conn, event.data)
            return
    # Handle RequestEndOfMessage events
    elif isinstance(event, _http1.RequestEndOfMessage):
        request = self.request
        manual_chunk = getattr(request, 'manual_chunk', False)
        if (
            "chunked" in request.headers.get("transfer-encoding", "").lower()
            and not manual_chunk  # Only send terminator if not manual_chunk
        ):
            yield _http1.commands.SendData(self.conn, b"0\r\n\r\n")
        yield from self.mark_done(request=True)
        return
    # Proceed with original behavior for other events
    yield from original_http1_client_send(self, event)


class ChunkedControlAddon:
    def load(self, loader):
        # Apply monkey patches
        _http1.Http1Server.send = new_http1_server_send
        _http1.Http1Client.send = new_http1_client_send

    def request(self, flow: http.HTTPFlow):
        # Check if the request has the special header
        if 'x-manual-chunk' in flow.request.headers:
            # Remove the header and set the manual_chunk flag
            del flow.request.headers['x-manual-chunk']
            flow.request.manual_chunk = True

    def response(self, flow: http.HTTPFlow):
        # Check if the response has the special header
        if 'x-manual-chunk' in flow.response.headers:
            # Remove the header and set the manual_chunk flag
            del flow.response.headers['x-manual-chunk']
            flow.response.manual_chunk = True


addons = [ChunkedControlAddon()]
