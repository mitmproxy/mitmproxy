from __future__ import absolute_import, print_function, division

import itertools
import sys
import traceback

import click

from typing import Optional  # noqa
import typing  # noqa

from mitmproxy import contentviews
from mitmproxy import controller
from mitmproxy import exceptions
from mitmproxy import filt
from mitmproxy import flow
from mitmproxy import builtins
from mitmproxy import utils
from netlib import human
from netlib import tcp
from netlib import strutils


class DumpError(Exception):
    pass


class Options(flow.options.Options):
    def __init__(
            self,
            filtstr=None,  # type: Optional[str]
            flow_detail=1,  # type: int
            keepserving=False,  # type: bool
            tfile=None,  # type: Optional[typing.io.TextIO]
            **kwargs
    ):
        self.filtstr = filtstr
        self.flow_detail = flow_detail
        self.keepserving = keepserving
        self.tfile = tfile
        super(Options, self).__init__(**kwargs)


class DumpMaster(flow.FlowMaster):

    def __init__(self, server, options):
        flow.FlowMaster.__init__(self, options, server, flow.State())
        self.has_errored = False
        self.addons.add(*builtins.default_addons())
        # This line is just for type hinting
        self.options = self.options  # type: Options
        self.o = options
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

        if options.rfile:
            try:
                self.load_flows_file(options.rfile)
            except exceptions.FlowReadException as v:
                self.add_log("Flow file corrupted.", "error")
                raise DumpError(v)

        if self.options.app:
            self.start_app(self.options.app_host, self.options.app_port)

    def _readflow(self, paths):
        """
        Utitility function that reads a list of flows
        or raises a DumpError if that fails.
        """
        try:
            return flow.read_flows_from_paths(paths)
        except exceptions.FlowReadException as e:
            raise DumpError(str(e))

    def add_log(self, e, level="info"):
        if level == "error":
            self.has_errored = True
        if self.options.verbosity >= utils.log_tier(level):
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
        click.secho(text, file=self.options.tfile, **style)

    def _echo_message(self, message):
        if self.options.flow_detail >= 2 and hasattr(message, "headers"):
            headers = "\r\n".join(
                "{}: {}".format(
                    click.style(strutils.bytes_to_escaped_str(k), fg="blue", bold=True),
                    click.style(strutils.bytes_to_escaped_str(v), fg="blue"))
                for k, v in message.headers.fields
            )
            self.echo(headers, indent=4)
        if self.options.flow_detail >= 3:
            try:
                content = message.content
            except ValueError:
                content = message.get_content(strict=False)

            if content is None:
                self.echo("(content missing)", indent=4)
            elif content:
                self.echo("")

                try:
                    type, lines = contentviews.get_content_view(
                        contentviews.get("Auto"),
                        content,
                        headers=getattr(message, "headers", None)
                    )
                except exceptions.ContentViewException:
                    s = "Content viewer failed: \n" + traceback.format_exc()
                    self.add_log(s, "debug")
                    type, lines = contentviews.get_content_view(
                        contentviews.get("Raw"),
                        content,
                        headers=getattr(message, "headers", None)
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

                if self.options.flow_detail == 3:
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

        if self.options.flow_detail >= 2:
            self.echo("")

    def _echo_request_line(self, flow):
        if flow.request.stickycookie:
            stickycookie = click.style(
                "[stickycookie] ", fg="yellow", bold=True
            )
        else:
            stickycookie = ""

        if flow.client_conn:
            client = click.style(strutils.escape_control_characters(flow.client_conn.address.host), bold=True)
        else:
            client = click.style("[replay]", fg="yellow", bold=True)

        method = flow.request.method
        method_color = dict(
            GET="green",
            DELETE="red"
        ).get(method.upper(), "magenta")
        method = click.style(strutils.escape_control_characters(method), fg=method_color, bold=True)
        if self.showhost:
            url = flow.request.pretty_url
        else:
            url = flow.request.url
        url = click.style(strutils.escape_control_characters(url), bold=True)

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
        reason = click.style(strutils.escape_control_characters(flow.response.reason), fg=code_color, bold=True)

        if flow.response.raw_content is None:
            size = "(content missing)"
        else:
            size = human.pretty_size(len(flow.response.raw_content))
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
        if self.options.flow_detail == 0:
            return

        if f.request:
            self._echo_request_line(f)
            self._echo_message(f.request)

        if f.response:
            self._echo_response_line(f)
            self._echo_message(f.response)

        if f.error:
            self.echo(" << {}".format(f.error.msg), bold=True, fg="red")

        if self.options.tfile:
            self.options.tfile.flush()

    def _process_flow(self, f):
        if self.filt and not f.match(self.filt):
            return

        self.echo_flow(f)

    @controller.handler
    def request(self, f):
        f = flow.FlowMaster.request(self, f)
        if f:
            self.state.delete_flow(f)
        return f

    @controller.handler
    def response(self, f):
        f = flow.FlowMaster.response(self, f)
        if f:
            self._process_flow(f)
        return f

    @controller.handler
    def error(self, f):
        flow.FlowMaster.error(self, f)
        if f:
            self._process_flow(f)
        return f

    @controller.handler
    def tcp_message(self, f):
        super(DumpMaster, self).tcp_message(f)

        if self.options.flow_detail == 0:
            return
        message = f.messages[-1]
        direction = "->" if message.from_client else "<-"
        self.echo("{client} {direction} tcp {direction} {server}".format(
            client=repr(f.client_conn.address),
            server=repr(f.server_conn.address),
            direction=direction,
        ))
        self._echo_message(message)

    def run(self):  # pragma: no cover
        if self.options.rfile and not self.options.keepserving:
            return
        super(DumpMaster, self).run()
