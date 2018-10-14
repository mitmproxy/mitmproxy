import itertools
import sys

import click
import shutil

import typing  # noqa

from mitmproxy import contentviews
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy.utils import human
from mitmproxy.utils import strutils


def indent(n: int, text: str) -> str:
    l = str(text).strip().splitlines()
    pad = " " * n
    return "\n".join(pad + i for i in l)


def colorful(line, styles):
    yield u"    "  # we can already indent here
    for (style, text) in line:
        yield click.style(text, **styles.get(style, {}))


class Dumper:
    def __init__(self, outfile=sys.stdout):
        self.filter: flowfilter.TFilter = None
        self.outfp: typing.io.TextIO = outfile

    def load(self, loader):
        loader.add_option(
            "flow_detail", int, 1,
            """
            The display detail level for flows in mitmdump: 0 (almost quiet) to 3 (very verbose).
              0: shortened request URL, response status code, WebSocket and TCP message notifications.
              1: full request URL with response status code
              2: 1 + HTTP headers
              3: 2 + full response content, content of WebSocket and TCP messages.
            """
        )
        loader.add_option(
            "dumper_default_contentview", str, "auto",
            "The default content view mode.",
            choices = [i.name.lower() for i in contentviews.views]
        )
        loader.add_option(
            "dumper_filter", typing.Optional[str], None,
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

    def echo(self, text, ident=None, **style):
        if ident:
            text = indent(ident, text)
        click.secho(text, file=self.outfp, **style)
        if self.outfp:
            self.outfp.flush()

    def _echo_headers(self, headers):
        for k, v in headers.fields:
            k = strutils.bytes_to_escaped_str(k)
            v = strutils.bytes_to_escaped_str(v)
            out = "{}: {}".format(
                click.style(k, fg="blue"),
                click.style(v)
            )
            self.echo(out, ident=4)

    def _echo_message(self, message):
        _, lines, error = contentviews.get_message_content_view(
            ctx.options.dumper_default_contentview,
            message
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

        content = u"\r\n".join(
            u"".join(colorful(line, styles)) for line in lines_to_echo
        )
        if content:
            self.echo("")
            self.echo(content)

        if next(lines, None):
            self.echo("(cut off)", ident=4, dim=True)

        if ctx.options.flow_detail >= 2:
            self.echo("")

    def _echo_request_line(self, flow):
        if flow.client_conn:
            client = click.style(
                strutils.escape_control_characters(
                    human.format_address(flow.client_conn.address)
                )
            )
        elif flow.request.is_replay:
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
        terminalWidthLimit = max(shutil.get_terminal_size()[0] - 25, 50)
        if ctx.options.flow_detail < 1 and len(url) > terminalWidthLimit:
            url = url[:terminalWidthLimit] + "…"
        url = click.style(strutils.escape_control_characters(url), bold=True)

        http_version = ""
        if flow.request.http_version not in ("HTTP/1.1", "HTTP/1.0"):
            # We hide "normal" HTTP 1.
            http_version = " " + flow.request.http_version

        line = "{client}: {method} {url}{http_version}".format(
            client=client,
            method=method,
            url=url,
            http_version=http_version
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
        code = click.style(
            str(code),
            fg=code_color,
            bold=True,
            blink=(code == 418)
        )
        reason = click.style(
            strutils.escape_control_characters(flow.response.reason),
            fg=code_color,
            bold=True
        )

        if flow.response.raw_content is None:
            size = "(content missing)"
        else:
            size = human.pretty_size(len(flow.response.raw_content))
        size = click.style(size, bold=True)

        arrows = click.style(" <<", bold=True)
        if ctx.options.flow_detail == 1:
            # This aligns the HTTP response code with the HTTP request method:
            # 127.0.0.1:59519: GET http://example.com/
            #               << 304 Not Modified 0b
            arrows = " " * (len(human.format_address(flow.client_conn.address)) - 2) + arrows

        line = "{replay}{arrows} {code} {reason} {size}".format(
            replay=replay,
            arrows=arrows,
            code=code,
            reason=reason,
            size=size
        )
        self.echo(line)

    def echo_flow(self, f):
        if f.request:
            self._echo_request_line(f)
            if ctx.options.flow_detail >= 2:
                self._echo_headers(f.request.headers)
            if ctx.options.flow_detail >= 3:
                self._echo_message(f.request)

        if f.response:
            self._echo_response_line(f)
            if ctx.options.flow_detail >= 2:
                self._echo_headers(f.response.headers)
            if ctx.options.flow_detail >= 3:
                self._echo_message(f.response)

        if f.error:
            msg = strutils.escape_control_characters(f.error.msg)
            self.echo(" << {}".format(msg), bold=True, fg="red")

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

    def websocket_error(self, f):
        self.echo(
            "Error in WebSocket connection to {}: {}".format(
                human.format_address(f.server_conn.address), f.error
            ),
            fg="red"
        )

    def websocket_message(self, f):
        if self.match(f):
            message = f.messages[-1]
            self.echo(f.message_info(message))
            if ctx.options.flow_detail >= 3:
                message = message.from_state(message.get_state())
                message.content = message.content.encode() if isinstance(message.content, str) else message.content
                self._echo_message(message)

    def websocket_end(self, f):
        if self.match(f):
            self.echo("WebSocket connection closed by {}: {} {}, {}".format(
                f.close_sender,
                f.close_code,
                f.close_message,
                f.close_reason))

    def tcp_error(self, f):
        self.echo(
            "Error in TCP connection to {}: {}".format(
                human.format_address(f.server_conn.address), f.error
            ),
            fg="red"
        )

    def tcp_message(self, f):
        if self.match(f):
            message = f.messages[-1]
            direction = "->" if message.from_client else "<-"
            self.echo("{client} {direction} tcp {direction} {server}".format(
                client=human.format_address(f.client_conn.address),
                server=human.format_address(f.server_conn.address),
                direction=direction,
            ))
            if ctx.options.flow_detail >= 3:
                self._echo_message(message)
