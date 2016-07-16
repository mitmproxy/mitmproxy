from __future__ import absolute_import, print_function, division

import itertools
import traceback

import click

from mitmproxy import contentviews
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import filt
from netlib import human
from netlib import strutils


def indent(n, text):
    l = str(text).strip().splitlines()
    pad = " " * n
    return "\n".join(pad + i for i in l)


class Dumper():
    def __init__(self):
        self.filter = None
        self.flow_detail = None
        self.outfp = None
        self.showhost = None

    def echo(self, text, ident=None, **style):
        if ident:
            text = indent(ident, text)
        click.secho(text, file=self.outfp, **style)

    def _echo_message(self, message):
        if self.flow_detail >= 2 and hasattr(message, "headers"):
            headers = "\r\n".join(
                "{}: {}".format(
                    click.style(strutils.bytes_to_escaped_str(k), fg="blue", bold=True),
                    click.style(strutils.bytes_to_escaped_str(v), fg="blue"))
                for k, v in message.headers.fields
            )
            self.echo(headers, ident=4)
        if self.flow_detail >= 3:
            try:
                content = message.content
            except ValueError:
                content = message.get_content(strict=False)

            if content is None:
                self.echo("(content missing)", ident=4)
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
                    ctx.log.debug(s)
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

                if self.flow_detail == 3:
                    lines_to_echo = itertools.islice(lines, 70)
                else:
                    lines_to_echo = lines

                lines_to_echo = list(lines_to_echo)

                content = u"\r\n".join(
                    u"".join(colorful(line)) for line in lines_to_echo
                )

                self.echo(content)
                if next(lines, None):
                    self.echo("(cut off)", ident=4, dim=True)

        if self.flow_detail >= 2:
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
        if self.flow_detail == 0:
            return

        if f.request:
            self._echo_request_line(f)
            self._echo_message(f.request)

        if f.response:
            self._echo_response_line(f)
            self._echo_message(f.response)

        if f.error:
            self.echo(" << {}".format(f.error.msg), bold=True, fg="red")

        if self.outfp:
            self.outfp.flush()

    def _process_flow(self, f):
        if self.filt and not f.match(self.filt):
            return
        self.echo_flow(f)

    def configure(self, options):
        if options.filtstr:
            self.filt = filt.parse(options.filtstr)
            if not self.filt:
                raise exceptions.OptionsError(
                    "Invalid filter expression: %s" % options.filtstr
                )
        else:
            self.filt = None
        self.flow_detail = options.flow_detail
        self.outfp = options.tfile
        self.showhost = options.showhost

    def response(self, f):
        self._process_flow(f)

    def error(self, f):
        self._process_flow(f)

    def tcp_message(self, f):
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
