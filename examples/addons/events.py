import typing

import mitmproxy.addonmanager
import mitmproxy.connections
import mitmproxy.http
import mitmproxy.log
import mitmproxy.tcp
import mitmproxy.websocket
import mitmproxy.proxy.protocol


class Events:
    # HTTP lifecycle
    def http_connect(self, flow: mitmproxy.http.HTTPFlow):
        """
            An HTTP CONNECT request was received. Setting a non 2xx response on
            the flow will return the response to the client abort the
            connection. CONNECT requests and responses do not generate the usual
            HTTP handler events. CONNECT requests are only valid in regular and
            upstream proxy modes.
        """

    def requestheaders(self, flow: mitmproxy.http.HTTPFlow):
        """
            HTTP request headers were successfully read. At this point, the body
            is empty.
        """

    def request(self, flow: mitmproxy.http.HTTPFlow):
        """
            The full HTTP request has been read.
        """

    def responseheaders(self, flow: mitmproxy.http.HTTPFlow):
        """
            HTTP response headers were successfully read. At this point, the body
            is empty.
        """

    def response(self, flow: mitmproxy.http.HTTPFlow):
        """
            The full HTTP response has been read.
        """

    def error(self, flow: mitmproxy.http.HTTPFlow):
        """
            An HTTP error has occurred, e.g. invalid server responses, or
            interrupted connections. This is distinct from a valid server HTTP
            error response, which is simply a response with an HTTP error code.
        """

    # TCP lifecycle
    def tcp_start(self, flow: mitmproxy.tcp.TCPFlow):
        """
            A TCP connection has started.
        """

    def tcp_message(self, flow: mitmproxy.tcp.TCPFlow):
        """
            A TCP connection has received a message. The most recent message
            will be flow.messages[-1]. The message is user-modifiable.
        """

    def tcp_error(self, flow: mitmproxy.tcp.TCPFlow):
        """
            A TCP error has occurred.
        """

    def tcp_end(self, flow: mitmproxy.tcp.TCPFlow):
        """
            A TCP connection has ended.
        """

    # Websocket lifecycle
    def websocket_handshake(self, flow: mitmproxy.http.HTTPFlow):
        """
            Called when a client wants to establish a WebSocket connection. The
            WebSocket-specific headers can be manipulated to alter the
            handshake. The flow object is guaranteed to have a non-None request
            attribute.
        """

    def websocket_start(self, flow: mitmproxy.websocket.WebSocketFlow):
        """
            A websocket connection has commenced.
        """

    def websocket_message(self, flow: mitmproxy.websocket.WebSocketFlow):
        """
            Called when a WebSocket message is received from the client or
            server. The most recent message will be flow.messages[-1]. The
            message is user-modifiable. Currently there are two types of
            messages, corresponding to the BINARY and TEXT frame types.
        """

    def websocket_error(self, flow: mitmproxy.websocket.WebSocketFlow):
        """
            A websocket connection has had an error.
        """

    def websocket_end(self, flow: mitmproxy.websocket.WebSocketFlow):
        """
            A websocket connection has ended.
        """

    # Network lifecycle
    def clientconnect(self, layer: mitmproxy.proxy.protocol.Layer):
        """
            A client has connected to mitmproxy. Note that a connection can
            correspond to multiple HTTP requests.
        """

    def clientdisconnect(self, layer: mitmproxy.proxy.protocol.Layer):
        """
            A client has disconnected from mitmproxy.
        """

    def serverconnect(self, conn: mitmproxy.connections.ServerConnection):
        """
            Mitmproxy has connected to a server. Note that a connection can
            correspond to multiple requests.
        """

    def serverdisconnect(self, conn: mitmproxy.connections.ServerConnection):
        """
            Mitmproxy has disconnected from a server.
        """

    def next_layer(self, layer: mitmproxy.proxy.protocol.Layer):
        """
            Network layers are being switched. You may change which layer will
            be used by returning a new layer object from this event.
        """

    # General lifecycle
    def configure(self, updated: typing.Set[str]):
        """
            Called when configuration changes. The updated argument is a
            set-like object containing the keys of all changed options. This
            event is called during startup with all options in the updated set.
        """

    def done(self):
        """
            Called when the addon shuts down, either by being removed from the
            mitmproxy instance, or when mitmproxy itself shuts down.
        """

    def load(self, entry: mitmproxy.addonmanager.Loader):
        """
            Called when an addon is first loaded. This event receives a Loader
            object, which contains methods for adding options and commands. This
            method is where the addon configures itself.
        """

    def log(self, entry: mitmproxy.log.LogEntry):
        """
            Called whenever a new log entry is created through the mitmproxy
            context. Be careful not to log from this event, which will cause an
            infinite loop!
        """

    def running(self):
        """
            Called when the proxy is completely up and running. At this point,
            you can expect the proxy to be bound to a port, and all addons to be
            loaded.
        """

    def update(self, flows: typing.Sequence[mitmproxy.flow.Flow]):
        """
            Update is called when one or more flow objects have been modified,
            usually from a different addon.
        """
