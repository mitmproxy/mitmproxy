"""
Process individual messages from a TCP connection.

This script replaces full occurrences of "foo" with "bar" and prints various details for each message.
Please note that TCP is stream-based and *not* message-based. mitmproxy splits stream contents into "messages"
as they are received by socket.recv(). This is pretty arbitrary and should not be relied on.
However, it is sometimes good enough as a quick hack.

Example Invocation:

    mitmdump --tcp-hosts ".*" -s examples/tcp-simple.py
"""

import logging

from mitmproxy import tcp
from mitmproxy.utils import strutils


def tcp_message(flow: tcp.TCPFlow):
    message = flow.messages[-1]
    message.content = message.content.replace(b"foo", b"bar")

    logging.info(
        f"tcp_message[from_client={message.from_client}), content={strutils.bytes_to_escaped_str(message.content)}]"
    )
