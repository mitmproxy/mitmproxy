"""Generic event hooks."""
import typing

import mitmproxy.addonmanager
import mitmproxy.connections
import mitmproxy.log
import mitmproxy.proxy.protocol


class Events:
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
        Called when the addon shuts down, either by being removed from
        the mitmproxy instance, or when mitmproxy itself shuts down. On
        shutdown, this event is called after the event loop is
        terminated, guaranteeing that it will be the final event an addon
        sees. Note that log handlers are shut down at this point, so
        calls to log functions will produce no output.
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
