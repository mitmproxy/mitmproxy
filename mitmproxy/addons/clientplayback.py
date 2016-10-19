from mitmproxy import exceptions, flow, ctx


class ClientPlayback:
    def __init__(self):
        self.flows = None
        self.current = None
        self.keepserving = None
        self.has_replayed = False

    def count(self):
        if self.flows:
            return len(self.flows)
        return 0

    def load(self, flows):
        self.flows = flows

    def configure(self, options, updated):
        if "client_replay" in updated:
            if options.client_replay:
                ctx.log.info(options.client_replay)
                try:
                    flows = flow.read_flows_from_paths(options.client_replay)
                except exceptions.FlowReadException as e:
                    raise exceptions.OptionsError(str(e))
                self.load(flows)
            else:
                self.flows = None
        self.keepserving = options.keepserving

    def tick(self):
        if self.current and not self.current.is_alive():
            self.current = None
        if self.flows and not self.current:
            self.current = ctx.master.replay_request(self.flows.pop(0))
            self.has_replayed = True
        if self.has_replayed:
            if not self.flows and not self.current and not self.keepserving:
                ctx.master.shutdown()
