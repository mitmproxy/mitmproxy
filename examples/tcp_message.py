"""
tcp_message Inline Script Hook API Demonstration
------------------------------------------------

* modifies packets containing "foo" to "bar"
* prints various details for each packet.

example cmdline invocation:
mitmdump -T --host --tcp ".*" -q -s examples/tcp_message.py
"""
from mitmproxy.utils import strutils


def tcp_message(tcp_msg):
    modified_msg = tcp_msg.message.replace("foo", "bar")

    is_modified = False if modified_msg == tcp_msg.message else True
    tcp_msg.message = modified_msg

    print(
        "[tcp_message{}] from {} {} to {} {}:\r\n{}".format(
            " (modified)" if is_modified else "",
            "client" if tcp_msg.sender == tcp_msg.client_conn else "server",
            tcp_msg.sender.address,
            "server" if tcp_msg.receiver == tcp_msg.server_conn else "client",
            tcp_msg.receiver.address, strutils.bytes_to_escaped_str(tcp_msg.message))
    )
