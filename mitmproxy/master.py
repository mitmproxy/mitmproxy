import sys
import traceback
import threading
import asyncio
import logging

from mitmproxy import addonmanager
from mitmproxy import options
from mitmproxy import controller
from mitmproxy import eventsequence
from mitmproxy import command
from mitmproxy import http
from mitmproxy import websocket
from mitmproxy import log
from mitmproxy.net import server_spec
from mitmproxy.coretypes import basethread

from . import ctx as mitmproxy_ctx


# Conclusively preventing cross-thread races on proxy shutdown turns out to be
# very hard. We could build a thread sync infrastructure for this, or we could
# wait until we ditch threads and move all the protocols into the async loop.
# Until then, silence non-critical errors.
logging.getLogger('asyncio').setLevel(logging.CRITICAL)


class ServerThread(basethread.BaseThread):
    def __init__(self, server):
        self.server = server
        address = getattr(self.server, "address", None)
        super().__init__(
            "ServerThread ({})".format(repr(address))
        )

    def run(self):
        self.server.serve_forever()


class Master:
    """
        The master handles mitmproxy's main event loop.
    """
    def __init__(self, opts):
        self.should_exit = threading.Event()
        self.channel = controller.Channel(
            self,
            asyncio.get_event_loop(),
            self.should_exit,
        )

        self.options: options.Options = opts or options.Options()
        self.commands = command.CommandManager(self)
        self.addons = addonmanager.AddonManager(self)
        self._server = None
        self.waiting_flows = []
        self.log = log.Log(self)

        mitmproxy_ctx.master = self
        mitmproxy_ctx.log = self.log
        mitmproxy_ctx.options = self.options

    @property
    def server(self):
        return self._server

    @server.setter
    def server(self, server):
        server.set_channel(self.channel)
        self._server = server

    def start(self):
        self.should_exit.clear()
        if self.server:
            ServerThread(self.server).start()

    async def running(self):
        self.addons.trigger("running")

    def run_loop(self, loop):
        self.start()
        asyncio.ensure_future(self.running())

        exc = None
        try:
            loop()
        except Exception as e:  # pragma: no cover
            exc = traceback.format_exc()
        finally:
            if not self.should_exit.is_set():  # pragma: no cover
                self.shutdown()
            loop = asyncio.get_event_loop()
            for p in asyncio.Task.all_tasks():
                p.cancel()
            loop.close()

        if exc:  # pragma: no cover
            print(exc, file=sys.stderr)
            print("mitmproxy has crashed!", file=sys.stderr)
            print("Please lodge a bug report at:", file=sys.stderr)
            print("\thttps://github.com/mitmproxy/mitmproxy", file=sys.stderr)

        self.addons.trigger("done")

    def run(self, func=None):
        loop = asyncio.get_event_loop()
        self.run_loop(loop.run_forever)

    async def _shutdown(self):
        self.should_exit.set()
        if self.server:
            self.server.shutdown()
        loop = asyncio.get_event_loop()
        loop.stop()

    def shutdown(self):
        """
            Shut down the proxy. This method is thread-safe.
        """
        if not self.should_exit.is_set():
            self.should_exit.set()
            ret = asyncio.run_coroutine_threadsafe(self._shutdown(), loop=self.channel.loop)
            # Weird band-aid to make sure that self._shutdown() is actually executed,
            # which otherwise hangs the process as the proxy server is threaded.
            # This all needs to be simplified when the proxy server runs on asyncio as well.
            if not self.channel.loop.is_running():  # pragma: no cover
                try:
                    self.channel.loop.run_until_complete(asyncio.wrap_future(ret))
                except RuntimeError:
                    pass  # Event loop stopped before Future completed.

    def _change_reverse_host(self, f):
        """
        When we load flows in reverse proxy mode, we adjust the target host to
        the reverse proxy destination for all flows we load. This makes it very
        easy to replay saved flows against a different host.
        """
        if self.options.mode.startswith("reverse:"):
            _, upstream_spec = server_spec.parse_with_mode(self.options.mode)
            f.request.host, f.request.port = upstream_spec.address
            f.request.scheme = upstream_spec.scheme

    async def load_flow(self, f):
        """
        Loads a flow and links websocket & handshake flows
        """

        if isinstance(f, http.HTTPFlow):
            self._change_reverse_host(f)
            if 'websocket' in f.metadata:
                self.waiting_flows.append(f)

        if isinstance(f, websocket.WebSocketFlow):
            hf = [hf for hf in self.waiting_flows if hf.id == f.metadata['websocket_handshake']][0]
            f.handshake_flow = hf
            self.waiting_flows.remove(hf)
            self._change_reverse_host(f.handshake_flow)

        f.reply = controller.DummyReply()
        for e, o in eventsequence.iterate(f):
            await self.addons.handle_lifecycle(e, o)
