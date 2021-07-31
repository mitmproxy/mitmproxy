import itertools
import shutil
from typing import IO, Optional, Union

import click

from mitmproxy import contentviews
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import http
from mitmproxy import flow
from mitmproxy.tcp import TCPFlow, TCPMessage
from mitmproxy.utils import human
from mitmproxy.utils import strutils
from mitmproxy.websocket import WebSocketMessage, WebSocketData
from wsproto.frame_protocol import CloseReason


def indent(n: int, text: str) -> str:
    l = str(text).strip().splitlines()
    pad = " " * n
    return "\n".join(pad + i for i in l)


def colorful(line, styles):
    yield "    "  # we can already indent here
    for (style, text) in line:
        yield click.style(text, **styles.get(style, {}))


class Dumper:
    def __init__(self, outfile=None):
        self.filter: Optional[flowfilter.TFilter] = None
        self.outfp: Optional[IO] = outfile

    def load(self, loader):
        loader.add_option(
            "flow_detail", int, 1,
            """
            The display detail level for flows in mitmdump: 0 (almost quiet) to 3 (very verbose).
              0: shortened request URL, response status code, WebSocket and TCP message notifications.
              1: full request URL with response status code
              2: 1 + HTTP headers
              3: 2 + truncated response content, content of WebSocket and TCP messages
              4: 3 + nothing is truncated
            """
        )
        loader.add_option(
            "dumper_default_contentview", str, "auto",
            "The default content view mode.",
            choices=[i.name.lower() for i in contentviews.views]
        )
        loader.add_option(
            "dumper_filter", Optional[str], None,
            "Limit which flows are dumped."
        )

    def configure(self, updated):
        if "dumper_filter" in updated:
            if ctx.options.dumper_filter:
                self.filter = flowfilter.parse(ctx.options.dumper_filter)
                if not self.filter:
                    raise exceptions.OptionsError(
                        "Invalid filter expression: %s" % ctx.options.dumper_filter
                    )
            else:
                self.filter = None

    def echo(self, text: str, ident=None, **style):
        if ident:
            text = indent(ident, text)
        click.secho(text, file=self.outfp, err=False, **style)
        if self.outfp:
            self.outfp.flush()

    def _echo_headers(self, headers: http.Headers):
        for k, v in headers.fields:
            ks = strutils.bytes_to_escaped_str(k)
            vs = strutils.bytes_to_escaped_str(v)
            out = "{}: {}".format(
                click.style(ks, fg="blue"),
                click.style(vs)
            )
            self.echo(out, ident=4)

    def _echo_trailers(self, trailers: Optional[http.Headers]):
        if not trailers:
            return
        self.echo(click.style("--- HTTP Trailers", fg="magenta"), ident=4)
        self._echo_headers(trailers)

    def _echo_message(
        self,
        message: Union[http.Message, TCPMessage, WebSocketMessage],
        flow: Union[http.HTTPFlow, TCPFlow]
    ):
        _, lines, error = contentviews.get_message_content_view(
            ctx.options.dumper_default_contentview,
            message,
            flow
        )
        if error:
            ctx.log.debug(error)

        if ctx.options.flow_detail == 3:
            lines_to_echo = itertools.islice(lines, 70)
        else:
            lines_to_echo = lines

        styles = dict(
            highlight=dict(bold=True),
            offset=dict(fg="blue"),
            header=dict(fg="green", bold=True),
            text=dict(fg="green")
        )

        content = "\r\n".join(
            "".join(colorful(line, styles)) for line in lines_to_echo
        )
        if content:
            self.echo("")
            self.echo(content)

        if next(lines, None):
            self.echo("(cut off)", ident=4, dim=True)

        if ctx.options.flow_detail >= 2:
            self.echo("")

    def _echo_request_line(self, flow: http.HTTPFlow) -> None:
        if flow.client_conn:
            client = click.style(
                strutils.escape_control_characters(
                    human.format_address(flow.client_conn.peername)
                )
            )
        elif flow.is_replay == "request":
            client = click.style("[replay]", fg="yellow", bold=True)
        else:
            client = ""

        pushed = ' PUSH_PROMISE' if 'h2-pushed-stream' in flow.metadata else ''
        method = flow.request.method + pushed
        method_color = dict(
            GET="green",
            DELETE="red"
        ).get(method.upper(), "magenta")
        method = click.style(
            strutils.escape_control_characters(method),
            fg=method_color,
            bold=True
        )
        if ctx.options.showhost:
            url = flow.request.pretty_url
        else:
            url = flow.request.url

        if ctx.options.flow_detail <= 1:
            # We need to truncate before applying styles, so we just focus on the URL.
            terminal_width_limit = max(shutil.get_terminal_size()[0] - 25, 50)
            if len(url) > terminal_width_limit:
                url = url[:terminal_width_limit] + "…"
        url = click.style(strutils.escape_control_characters(url), bold=True)

        http_version = ""
        if (
            not (flow.request.is_http10 or flow.request.is_http11)
            or flow.request.http_version != getattr(flow.response, "http_version", "HTTP/1.1")
        ):
            # Hide version for h1 <-> h1 connections.
            http_version = " " + flow.request.http_version

        self.echo(f"{client}: {method} {url}{http_version}")

    def _echo_response_line(self, flow: http.HTTPFlow) -> None:
        if flow.is_replay == "response":
            replay_str = "[replay]"
            replay = click.style(replay_str, fg="yellow", bold=True)
        else:
            replay_str = ""
            replay = ""

        assert flow.response
        code_int = flow.response.status_code
        code_color = None
        if 200 <= code_int < 300:
            code_color = "green"
        elif 300 <= code_int < 400:
            code_color = "magenta"
        elif 400 <= code_int < 600:
            code_color = "red"
        code = click.style(
            str(code_int),
            fg=code_color,
            bold=True,
            blink=(code_int == 418),
        )

        if not flow.response.is_http2:
            reason = flow.response.reason
        else:
            reason = http.status_codes.RESPONSES.get(flow.response.status_code, "")
        reason = click.style(
            strutils.escape_control_characters(reason),
            fg=code_color,
            bold=True
        )

        if flow.response.raw_content is None:
            size = "(content missing)"
        else:
            size = human.pretty_size(len(flow.response.raw_content))
        size = click.style(size, bold=True)

        http_version = ""
        if (
            not (flow.response.is_http10 or flow.response.is_http11)
            or flow.request.http_version != flow.response.http_version
        ):
            # Hide version for h1 <-> h1 connections.
            http_version = f"{flow.response.http_version} "

        arrows = click.style(" <<", bold=True)
        if ctx.options.flow_detail == 1:
            # This aligns the HTTP response code with the HTTP request method:
            # 127.0.0.1:59519: GET http://example.com/
            #               << 304 Not Modified 0b
            pad = max(0,
                      len(human.format_address(flow.client_conn.peername)) - (2 + len(http_version) + len(replay_str)))
            arrows = " " * pad + arrows

        self.echo(f"{replay}{arrows} {http_version}{code} {reason} {size}")

    def echo_flow(self, f: http.HTTPFlow) -> None:
        if f.request:
            self._echo_request_line(f)
            if ctx.options.flow_detail >= 2:
                self._echo_headers(f.request.headers)
            if ctx.options.flow_detail >= 3:
                self._echo_message(f.request, f)
            if ctx.options.flow_detail >= 2:
                self._echo_trailers(f.request.trailers)

        if f.response:
            self._echo_response_line(f)
            if ctx.options.flow_detail >= 2:
                self._echo_headers(f.response.headers)
            if ctx.options.flow_detail >= 3:
                self._echo_message(f.response, f)
            if ctx.options.flow_detail >= 2:
                self._echo_trailers(f.response.trailers)

        if f.error:
            msg = strutils.escape_control_characters(f.error.msg)
            self.echo(f" << {msg}", bold=True, fg="red")

    def match(self, f):
        if ctx.options.flow_detail == 0:
            return False
        if not self.filter:
            return True
        elif flowfilter.match(self.filter, f):
            return True
        return False

    def response(self, f):
        if self.match(f):
            self.echo_flow(f)

    def error(self, f):
        if self.match(f):
            self.echo_flow(f)

    def websocket_message(self, f: http.HTTPFlow):
        assert f.websocket is not None  # satisfy type checker
        if self.match(f):
            message = f.websocket.messages[-1]

            direction = "->" if message.from_client else "<-"
            self.echo(
                f"{human.format_address(f.client_conn.peername)} "
                f"{direction} WebSocket {message.type.name.lower()} message "
                f"{direction} {human.format_address(f.server_conn.address)}{f.request.path}"
            )
            if ctx.options.flow_detail >= 3:
                self._echo_message(message, f)

    def websocket_end(self, f: http.HTTPFlow):
        assert f.websocket is not None  # satisfy type checker
        if self.match(f):
            if f.websocket.close_code in {1000, 1001, 1005}:
                c = 'client' if f.websocket.closed_by_client else 'server'
                self.echo(f"WebSocket connection closed by {c}: {f.websocket.close_code} {f.websocket.close_reason}")
            else:
                error = flow.Error(f"WebSocket Error: {self.format_websocket_error(f.websocket)}")
                self.echo(
                    f"Error in WebSocket connection to {human.format_address(f.server_conn.address)}: {error}",
                    fg="red"
                )

    def format_websocket_error(self, websocket: WebSocketData) -> str:
        try:
            ret = CloseReason(websocket.close_code).name
        except ValueError:
            ret = f"UNKNOWN_ERROR={websocket.close_code}"
        if websocket.close_reason:
            ret += f" (reason: {websocket.close_reason})"
        return ret

    def tcp_error(self, f):
        if self.match(f):
            self.echo(
                f"Error in TCP connection to {human.format_address(f.server_conn.address)}: {f.error}",
                fg="red"
            )

    def tcp_message(self, f):
        if self.match(f):
            message = f.messages[-1]
            direction = "->" if message.from_client else "<-"
            self.echo("{client} {direction} tcp {direction} {server}".format(
                client=human.format_address(f.client_conn.peername),
                server=human.format_address(f.server_conn.address),
                direction=direction,
            ))
            if ctx.options.flow_detail >= 3:
                self._echo_message(message, f)
