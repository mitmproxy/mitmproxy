import hashlib
import typing
import urllib

import mitmproxy.types
from mitmproxy import command, hooks
from mitmproxy import ctx, http
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import io


class ServerPlayback:
    flowmap: typing.Dict[typing.Hashable, typing.List[http.HTTPFlow]]
    configured: bool

    def __init__(self):
        self.flowmap = {}
        self.configured = False

    def load(self, loader):
        loader.add_option(
            "server_replay_kill_extra", bool, False,
            "Kill extra requests during replay."
        )
        loader.add_option(
            "server_replay_nopop", bool, False,
            """
            Don't remove flows from server replay state after use. This makes it
            possible to replay same response multiple times.
            """
        )
        loader.add_option(
            "server_replay_refresh", bool, True,
            """
            Refresh server replay responses by adjusting date, expires and
            last-modified headers, as well as adjusting cookie expiration.
            """
        )
        loader.add_option(
            "server_replay_use_headers", typing.Sequence[str], [],
            "Request headers to be considered during replay."
        )
        loader.add_option(
            "server_replay", typing.Sequence[str], [],
            "Replay server responses from a saved file."
        )
        loader.add_option(
            "server_replay_ignore_content", bool, False,
            "Ignore request's content while searching for a saved flow to replay."
        )
        loader.add_option(
            "server_replay_ignore_params", typing.Sequence[str], [],
            """
            Request's parameters to be ignored while searching for a saved flow
            to replay.
            """
        )
        loader.add_option(
            "server_replay_ignore_payload_params", typing.Sequence[str], [],
            """
            Request's payload parameters (application/x-www-form-urlencoded or
            multipart/form-data) to be ignored while searching for a saved flow
            to replay.
            """
        )
        loader.add_option(
            "server_replay_ignore_host", bool, False,
            """
            Ignore request's destination host while searching for a saved flow
            to replay.
            """
        )
        loader.add_option(
            "server_replay_ignore_port", bool, False,
            """
            Ignore request's destination port while searching for a saved flow
            to replay.
            """
        )

    @command.command("replay.server")
    def load_flows(self, flows: typing.Sequence[flow.Flow]) -> None:
        """
            Replay server responses from flows.
        """
        self.flowmap = {}
        for f in flows:
            if isinstance(f, http.HTTPFlow):
                lst = self.flowmap.setdefault(self._hash(f), [])
                lst.append(f)
        ctx.master.addons.trigger(hooks.UpdateHook([]))

    @command.command("replay.server.file")
    def load_file(self, path: mitmproxy.types.Path) -> None:
        try:
            flows = io.read_flows_from_paths([path])
        except exceptions.FlowReadException as e:
            raise exceptions.CommandError(str(e))
        self.load_flows(flows)

    @command.command("replay.server.stop")
    def clear(self) -> None:
        """
            Stop server replay.
        """
        self.flowmap = {}
        ctx.master.addons.trigger(hooks.UpdateHook([]))

    @command.command("replay.server.count")
    def count(self) -> int:
        return sum([len(i) for i in self.flowmap.values()])

    def _hash(self, flow: http.HTTPFlow) -> typing.Hashable:
        """
            Calculates a loose hash of the flow request.
        """
        r = flow.request
        _, _, path, _, query, _ = urllib.parse.urlparse(r.url)
        queriesArray = urllib.parse.parse_qsl(query, keep_blank_values=True)

        key: typing.List[typing.Any] = [str(r.scheme), str(r.method), str(path)]
        if not ctx.options.server_replay_ignore_content:
            if ctx.options.server_replay_ignore_payload_params and r.multipart_form:
                key.extend(
                    (k, v)
                    for k, v in r.multipart_form.items(multi=True)
                    if k.decode(errors="replace") not in ctx.options.server_replay_ignore_payload_params
                )
            elif ctx.options.server_replay_ignore_payload_params and r.urlencoded_form:
                key.extend(
                    (k, v)
                    for k, v in r.urlencoded_form.items(multi=True)
                    if k not in ctx.options.server_replay_ignore_payload_params
                )
            else:
                key.append(str(r.raw_content))

        if not ctx.options.server_replay_ignore_host:
            key.append(r.pretty_host)
        if not ctx.options.server_replay_ignore_port:
            key.append(r.port)

        filtered = []
        ignore_params = ctx.options.server_replay_ignore_params or []
        for p in queriesArray:
            if p[0] not in ignore_params:
                filtered.append(p)
        for p in filtered:
            key.append(p[0])
            key.append(p[1])

        if ctx.options.server_replay_use_headers:
            headers = []
            for i in ctx.options.server_replay_use_headers:
                v = r.headers.get(i)
                headers.append((i, v))
            key.append(headers)
        return hashlib.sha256(
            repr(key).encode("utf8", "surrogateescape")
        ).digest()

    def next_flow(self, flow: http.HTTPFlow) -> typing.Optional[http.HTTPFlow]:
        """
            Returns the next flow object, or None if no matching flow was
            found.
        """
        hash = self._hash(flow)
        if hash in self.flowmap:
            if ctx.options.server_replay_nopop:
                return next((
                    flow
                    for flow in self.flowmap[hash]
                    if flow.response
                ), None)
            else:
                ret = self.flowmap[hash].pop(0)
                while not ret.response:
                    if self.flowmap[hash]:
                        ret = self.flowmap[hash].pop(0)
                    else:
                        del self.flowmap[hash]
                        return None
                if not self.flowmap[hash]:
                    del self.flowmap[hash]
                return ret
        else:
            return None

    def configure(self, updated):
        if not self.configured and ctx.options.server_replay:
            self.configured = True
            try:
                flows = io.read_flows_from_paths(ctx.options.server_replay)
            except exceptions.FlowReadException as e:
                raise exceptions.OptionsError(str(e))
            self.load_flows(flows)

    def request(self, f: http.HTTPFlow) -> None:
        if self.flowmap:
            rflow = self.next_flow(f)
            if rflow:
                assert rflow.response
                response = rflow.response.copy()
                if ctx.options.server_replay_refresh:
                    response.refresh()
                f.response = response
                f.is_replay = "response"
            elif ctx.options.server_replay_kill_extra:
                ctx.log.warn(
                    "server_playback: killed non-replay request {}".format(
                        f.request.url
                    )
                )
                f.kill()
