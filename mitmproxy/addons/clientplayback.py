from mitmproxy import exceptions
from mitmproxy import ctx
from mitmproxy import io
from mitmproxy import flow

import typing


class ClientPlayback:
    def __init__(self):
        self.flows = None
        self.current_thread = None
        self.keepserving = False
        self.has_replayed = False

    def count(self) -> int:
        if self.flows:
            return len(self.flows)
        return 0

    def load(self, flows: typing.Sequence[flow.Flow]):
        self.flows = flows

    def configure(self, options, updated):
        if "client_replay" in updated:
            if options.client_replay:
                ctx.log.info("Client Replay: {}".format(options.client_replay))
                try:
                    flows = io.read_flows_from_paths(options.client_replay)
                except exceptions.FlowReadException as e:
                    raise exceptions.OptionsError(str(e))
                self.load(flows)
            else:
                self.flows = None
        self.keepserving = options.keepserving

    def tick(self):
        if self.current_thread and not self.current_thread.is_alive():
            self.current_thread = None
        if self.flows and not self.current_thread:
            self.current_thread = ctx.master.replay_request(self.flows.pop(0))
            self.has_replayed = True
        if self.has_replayed:
            if not self.flows and not self.current_thread and not self.keepserving:
                ctx.master.shutdown()
