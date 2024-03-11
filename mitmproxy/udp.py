import time

from mitmproxy import connection
from mitmproxy import flow
from mitmproxy.coretypes import serializable


class UDPMessage(serializable.Serializable):
    """
    An individual UDP datagram.
    """

    def __init__(self, from_client, content, timestamp=None):
        self.from_client = from_client
        self.content = content
        self.timestamp = timestamp or time.time()

    @classmethod
    def from_state(cls, state):
        return cls(*state)

    def get_state(self):
        return self.from_client, self.content, self.timestamp

    def set_state(self, state):
        self.from_client, self.content, self.timestamp = state

    def __repr__(self):
        return "{direction} {content}".format(
            direction="->" if self.from_client else "<-", content=repr(self.content)
        )


class UDPFlow(flow.Flow):
    """
    A UDPFlow is a representation of a UDP session.
    """

    messages: list[UDPMessage]
    """
    The messages transmitted over this connection.

    The latest message can be accessed as `flow.messages[-1]` in event hooks.
    """

    def __init__(
        self,
        client_conn: connection.Client,
        server_conn: connection.Server,
        live: bool = False,
    ):
        super().__init__(client_conn, server_conn, live)
        self.messages = []

    def get_state(self) -> serializable.State:
        return {
            **super().get_state(),
            "messages": [m.get_state() for m in self.messages],
        }

    def set_state(self, state: serializable.State) -> None:
        self.messages = [UDPMessage.from_state(m) for m in state.pop("messages")]
        super().set_state(state)

    def __repr__(self):
        return f"<UDPFlow ({len(self.messages)} messages)>"


__all__ = [
    "UDPFlow",
    "UDPMessage",
]
