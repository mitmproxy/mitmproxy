"""
tcp_message Inline Script Hook API Demonstration
------------------------------------------------

* modifies packets containing "foo" to "bar"
* prints various details for each packet.

example cmdline invocation:
mitmdump --rawtcp --tcp-host ".*" -s examples/complex/tcp_message.py
"""
from mitmproxy.utils import strutils
from mitmproxy import ctx
from mitmproxy import tcp


def tcp_message(flow: tcp.TCPFlow):
    message = flow.messages[-1]
    old_content = message.content
    message.content = old_content.replace(b"foo", b"bar")

    ctx.log.info(
        "[tcp_message{}] from {} to {}:\n{}".format(
            " (modified)" if message.content != old_content else "",
            "client" if message.from_client else "server",
            "server" if message.from_client else "client",
            strutils.bytes_to_escaped_str(message.content))
    )
