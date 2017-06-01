from mitmproxy import exceptions
from mitmproxy import ctx
from mitmproxy import io
from mitmproxy import flow
from mitmproxy import command

import typing


class ClientPlayback:
    def __init__(self):
        self.flows = None
        self.current_thread = None
        self.has_replayed = False
        self.configured = False

    def count(self) -> int:
        if self.flows:
            return len(self.flows)
        return 0

    @command.command("replay.client.stop")
    def stop_replay(self) -> None:
        """
            Stop client replay.
        """
        self.flows = []
        ctx.master.addons.trigger("update", [])

    @command.command("replay.client")
    def start_replay(self, flows: typing.Sequence[flow.Flow]) -> None:
        """
            Replay requests from flows.
        """
        self.flows = flows
        ctx.master.addons.trigger("update", [])

    @command.command("replay.client.file")
    def load_file(self, path: str) -> None:
        try:
            flows = io.read_flows_from_paths([path])
        except exceptions.FlowReadException as e:
            raise exceptions.CommandError(str(e))
        self.flows = flows

    def configure(self, updated):
        if not self.configured and ctx.options.client_replay:
            self.configured = True
            ctx.log.info("Client Replay: {}".format(ctx.options.client_replay))
            try:
                flows = io.read_flows_from_paths(ctx.options.client_replay)
            except exceptions.FlowReadException as e:
                raise exceptions.OptionsError(str(e))
            self.start_replay(flows)

    def tick(self):
        if self.current_thread and not self.current_thread.is_alive():
            self.current_thread = None
        if self.flows and not self.current_thread:
            f = self.flows.pop(0)
            self.current_thread = ctx.master.replay_request(f)
            ctx.master.addons.trigger("update", [f])
            self.has_replayed = True
        if self.has_replayed:
            if not self.flows and not self.current_thread:
                ctx.master.addons.trigger("processing_complete")
