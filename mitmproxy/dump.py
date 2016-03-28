from __future__ import absolute_import, print_function
import traceback
import sys
import click
import itertools

from netlib import tcp
import netlib.utils
from . import flow, filt, contentviews
from .exceptions import ContentViewException


class DumpError(Exception):
    pass


class Options(object):
    attributes = [
        "app",
        "app_host",
        "app_port",
        "anticache",
        "anticomp",
        "client_replay",
        "filtstr",
        "flow_detail",
        "keepserving",
        "kill",
        "no_server",
        "nopop",
        "refresh_server_playback",
        "replacements",
        "rfile",
        "rheaders",
        "setheaders",
        "server_replay",
        "scripts",
        "showhost",
        "stickycookie",
        "stickyauth",
        "stream_large_bodies",
        "verbosity",
        "outfile",
        "replay_ignore_content",
        "replay_ignore_params",
        "replay_ignore_payload_params",
        "replay_ignore_host"
    ]

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        for i in self.attributes:
            if not hasattr(self, i):
                setattr(self, i, None)


class DumpMaster(flow.FlowMaster):

    def __init__(self, server, options, outfile=None):
        flow.FlowMaster.__init__(self, server, flow.State())
        self.outfile = outfile
        self.o = options
        self.anticache = options.anticache
        self.anticomp = options.anticomp
        self.showhost = options.showhost
        self.replay_ignore_params = options.replay_ignore_params
        self.replay_ignore_content = options.replay_ignore_content
        self.replay_ignore_host = options.replay_ignore_host
        self.refresh_server_playback = options.refresh_server_playback
        self.replay_ignore_payload_params = options.replay_ignore_payload_params

        self.set_stream_large_bodies(options.stream_large_bodies)

        if self.server and self.server.config.http2 and not tcp.HAS_ALPN:  # pragma: no cover
            print("ALPN support missing (OpenSSL 1.0.2+ required)!\n"
                "HTTP/2 is disabled. Use --no-http2 to silence this warning.",
                file=sys.stderr)

        if options.filtstr:
            self.filt = filt.parse(options.filtstr)
        else:
            self.filt = None

        if options.stickycookie:
            self.set_stickycookie(options.stickycookie)

        if options.stickyauth:
            self.set_stickyauth(options.stickyauth)

        if options.outfile:
            err = self.start_stream_to_path(
                options.outfile[0],
                options.outfile[1]
            )
            if err:
                raise DumpError(err)

        if options.replacements:
            for i in options.replacements:
                self.replacehooks.add(*i)

        if options.setheaders:
            for i in options.setheaders:
                self.setheaders.add(*i)

        if options.server_replay:
            self.start_server_playback(
                self._readflow(options.server_replay),
                options.kill, options.rheaders,
                not options.keepserving,
                options.nopop,
                options.replay_ignore_params,
                options.replay_ignore_content,
                options.replay_ignore_payload_params,
                options.replay_ignore_host
            )

        if options.client_replay:
            self.start_client_playback(
                self._readflow(options.client_replay),
                not options.keepserving
            )

        scripts = options.scripts or []
        for command in scripts:
            err = self.load_script(command, use_reloader=True)
            if err:
                raise DumpError(err)

        if options.rfile:
            try:
                self.load_flows_file(options.rfile)
            except flow.FlowReadError as v:
                self.add_event("Flow file corrupted.", "error")
                raise DumpError(v)

        if self.o.app:
            self.start_app(self.o.app_host, self.o.app_port)

    def _readflow(self, paths):
        """
        Utitility function that reads a list of flows
        or raises a DumpError if that fails.
        """
        try:
            return flow.read_flows_from_paths(paths)
        except flow.FlowReadError as e:
            raise DumpError(e.strerror)

    def add_event(self, e, level="info"):
        needed = dict(error=0, info=1, debug=2).get(level, 1)
        if self.o.verbosity >= needed:
            self.echo(
                e,
                fg="red" if level == "error" else None,
                dim=(level == "debug"),
                err=(level == "error")
            )

    @staticmethod
    def indent(n, text):
        l = str(text).strip().splitlines()
        pad = " " * n
        return "\n".join(pad + i for i in l)

    def echo(self, text, indent=None, **style):
        if indent:
            text = self.indent(indent, text)
        click.secho(text, file=self.outfile, **style)

    def _echo_message(self, message):
        if self.o.flow_detail >= 2:
            headers = "\r\n".join(
                "{}: {}".format(
                    click.style(k, fg="blue", bold=True),
                    click.style(v, fg="blue"))
                for k, v in message.headers.fields
            )
            self.echo(headers, indent=4)
        if self.o.flow_detail >= 3:
            if message.content is None:
                self.echo("(content missing)", indent=4)
            elif message.content:
                self.echo("")

                try:
                    type, lines = contentviews.get_content_view(
                        contentviews.get("Auto"),
                        message.content,
                        headers=message.headers
                    )
                except ContentViewException:
                    s = "Content viewer failed: \n" + traceback.format_exc()
                    self.add_event(s, "debug")
                    type, lines = contentviews.get_content_view(
                        contentviews.get("Raw"),
                        message.content,
                        headers=message.headers
                    )

                styles = dict(
                    highlight=dict(bold=True),
                    offset=dict(fg="blue"),
                    header=dict(fg="green", bold=True),
                    text=dict(fg="green")
                )

                def colorful(line):
                    yield u"    "  # we can already indent here
                    for (style, text) in line:
                        yield click.style(text, **styles.get(style, {}))

                if self.o.flow_detail == 3:
                    lines_to_echo = itertools.islice(lines, 70)
                else:
                    lines_to_echo = lines

                lines_to_echo = list(lines_to_echo)

                content = u"\r\n".join(
                    u"".join(colorful(line)) for line in lines_to_echo
                )

                self.echo(content)
                if next(lines, None):
                    self.echo("(cut off)", indent=4, dim=True)

        if self.o.flow_detail >= 2:
            self.echo("")

    def _echo_request_line(self, flow):
        if flow.request.stickycookie:
            stickycookie = click.style("[stickycookie] ", fg="yellow", bold=True)
        else:
            stickycookie = ""

        if flow.client_conn:
            client = click.style(flow.client_conn.address.host, bold=True)
        else:
            client = click.style("[replay]", fg="yellow", bold=True)

        method = flow.request.method
        method_color = dict(
            GET="green",
            DELETE="red"
        ).get(method.upper(), "magenta")
        method = click.style(method, fg=method_color, bold=True)
        if self.showhost:
            url = flow.request.pretty_url
        else:
            url = flow.request.url
        url = click.style(url, bold=True)

        httpversion = ""
        if flow.request.http_version not in ("HTTP/1.1", "HTTP/1.0"):
            httpversion = " " + flow.request.http_version  # We hide "normal" HTTP 1.

        line = "{stickycookie}{client} {method} {url}{httpversion}".format(
            stickycookie=stickycookie,
            client=client,
            method=method,
            url=url,
            httpversion=httpversion
        )
        self.echo(line)

    def _echo_response_line(self, flow):
        if flow.response.is_replay:
            replay = click.style("[replay] ", fg="yellow", bold=True)
        else:
            replay = ""

        code = flow.response.status_code
        code_color = None
        if 200 <= code < 300:
            code_color = "green"
        elif 300 <= code < 400:
            code_color = "magenta"
        elif 400 <= code < 600:
            code_color = "red"
        code = click.style(str(code), fg=code_color, bold=True, blink=(code == 418))
        reason = click.style(flow.response.reason, fg=code_color, bold=True)

        if flow.response.content is None:
            size = "(content missing)"
        else:
            size = netlib.utils.pretty_size(len(flow.response.content))
        size = click.style(size, bold=True)

        arrows = click.style("<<", bold=True)

        line = "{replay} {arrows} {code} {reason} {size}".format(
            replay=replay,
            arrows=arrows,
            code=code,
            reason=reason,
            size=size
        )
        self.echo(line)

    def echo_flow(self, f):
        if self.o.flow_detail == 0:
            return

        if f.request:
            self._echo_request_line(f)
            self._echo_message(f.request)

        if f.response:
            self._echo_response_line(f)
            self._echo_message(f.response)

        if f.error:
            self.echo(" << {}".format(f.error.msg), bold=True, fg="red")

        if self.outfile:
            self.outfile.flush()

    def _process_flow(self, f):
        self.state.delete_flow(f)
        if self.filt and not f.match(self.filt):
            return

        self.echo_flow(f)

    def handle_request(self, f):
        flow.FlowMaster.handle_request(self, f)
        if f:
            f.reply()
        return f

    def handle_response(self, f):
        flow.FlowMaster.handle_response(self, f)
        if f:
            f.reply()
            self._process_flow(f)
        return f

    def handle_error(self, f):
        flow.FlowMaster.handle_error(self, f)
        if f:
            self._process_flow(f)
        return f

    def shutdown(self):  # pragma: no cover
        return flow.FlowMaster.shutdown(self)

    def run(self):  # pragma: no cover
        if self.o.rfile and not self.o.keepserving:
            self.shutdown()
            return
        try:
            return flow.FlowMaster.run(self)
        except BaseException:
            self.shutdown()
            raise
