from mitmproxy import exceptions
from mitmproxy import io

from mitmproxy.addons import serverplayback


class ServerCachePlayBack(serverplayback.ServerPlayback):
    def __init__(self):
        super().__init__()
        self._enabled = False

    def load(self, flows):
        for i in flows:
            if i.response:
                self.flowmap[self._hash(i)] = i

    def enable(self, flows=None):
        self._enabled = True
        if flows:
            self.load(flows)

    def disable(self):
        self._enabled = False
        self.clear()

    @property
    def enabled(self):
        return self._enabled

    def configure(self, options, updated):
        self.options = options
        if "server_cache_replay" in updated:
            if options.server_cache_replay:
                flows = []
                if options.server_cache_replay_load:
                    try:
                        flows = io.read_flows_from_paths(options.server_cache_replay_load)
                    except exceptions.FlowReadException as e:
                        raise exceptions.OptionsError(str(e))
                self.enable(flows=flows)
            else:
                self.disable()

    def request(self, f):
        if not self._enabled:
            return

        flow_hash = self._hash(f)
        # First check if the flow exists in our known flow_hash, if it doesn't, let's add it
        # and proceed without replaying it.
        known_flow = self.flowmap.get(flow_hash)
        if not known_flow:
            self.flowmap[flow_hash] = f
            return

        # Otherwise, let's turn the current flow response into our known response
        response = known_flow.response.copy()
        response.is_replay = True
        f.response = response
