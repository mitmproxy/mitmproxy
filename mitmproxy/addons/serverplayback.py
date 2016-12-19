import hashlib
import urllib
from typing import Any  # noqa
from typing import List  # noqa

from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import io


class ServerPlayback:
    def __init__(self):
        self.options = None

        self.flowmap = {}
        self.stop = False
        self.final_flow = None

    def load(self, flows):
        for i in flows:
            if i.response:
                l = self.flowmap.setdefault(self._hash(i), [])
                l.append(i)

    def clear(self):
        self.flowmap = {}

    def count(self):
        return sum([len(i) for i in self.flowmap.values()])

    def _hash(self, flow):
        """
            Calculates a loose hash of the flow request.
        """
        r = flow.request

        _, _, path, _, query, _ = urllib.parse.urlparse(r.url)
        queriesArray = urllib.parse.parse_qsl(query, keep_blank_values=True)

        key = [str(r.port), str(r.scheme), str(r.method), str(path)]  # type: List[Any]
        if not self.options.server_replay_ignore_content:
            if self.options.server_replay_ignore_payload_params and r.multipart_form:
                key.extend(
                    (k, v)
                    for k, v in r.multipart_form.items(multi=True)
                    if k.decode(errors="replace") not in self.options.server_replay_ignore_payload_params
                )
            elif self.options.server_replay_ignore_payload_params and r.urlencoded_form:
                key.extend(
                    (k, v)
                    for k, v in r.urlencoded_form.items(multi=True)
                    if k not in self.options.server_replay_ignore_payload_params
                )
            else:
                key.append(str(r.raw_content))

        if not self.options.server_replay_ignore_host:
            key.append(r.host)

        filtered = []
        ignore_params = self.options.server_replay_ignore_params or []
        for p in queriesArray:
            if p[0] not in ignore_params:
                filtered.append(p)
        for p in filtered:
            key.append(p[0])
            key.append(p[1])

        if self.options.server_replay_use_headers:
            headers = []
            for i in self.options.server_replay_use_headers:
                v = r.headers.get(i)
                headers.append((i, v))
            key.append(headers)
        return hashlib.sha256(
            repr(key).encode("utf8", "surrogateescape")
        ).digest()

    def next_flow(self, request):
        """
            Returns the next flow object, or None if no matching flow was
            found.
        """
        hsh = self._hash(request)
        if hsh in self.flowmap:
            if self.options.server_replay_nopop:
                return self.flowmap[hsh][0]
            else:
                ret = self.flowmap[hsh].pop(0)
                if not self.flowmap[hsh]:
                    del self.flowmap[hsh]
                return ret

    def configure(self, options, updated):
        self.options = options
        if "server_replay" in updated:
            self.clear()
            if options.server_replay:
                try:
                    flows = io.read_flows_from_paths(options.server_replay)
                except exceptions.FlowReadException as e:
                    raise exceptions.OptionsError(str(e))
                self.load(flows)

    def tick(self):
        if self.stop and not self.final_flow.live:
            ctx.master.shutdown()

    def request(self, f):
        if self.flowmap:
            rflow = self.next_flow(f)
            if rflow:
                response = rflow.response.copy()
                response.is_replay = True
                if self.options.refresh_server_playback:
                    response.refresh()
                f.response = response
                if not self.flowmap and not self.options.keepserving:
                    self.final_flow = f
                    self.stop = True
            elif self.options.replay_kill_extra:
                ctx.log.warn(
                    "server_playback: killed non-replay request {}".format(
                        f.request.url
                    )
                )
                f.reply.kill()
