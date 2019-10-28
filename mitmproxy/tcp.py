import time

import uuid
from typing import List

from mitmproxy import flow
from mitmproxy.utils import human
from mitmproxy.coretypes import serializable


class TCPMessage(serializable.Serializable):

    def __init__(self, from_client, raw, timestamp=None):
        self.from_client = from_client
        self.id = str(uuid.uuid4())
        self._raw_content = raw 
        self.timestamp = timestamp or time.time()

    @classmethod
    def from_state(cls, state):
        return cls(*state)

    @property
    def content(self):
        return self.raw_content
        #TODO figure out raw/content distinction 

    @property
    def raw_content(self):
        return self._raw_content
        #TODO figure out raw/content distinction 

    @raw_content.setter
    def raw_content(self, raw):
        self._raw_content = raw

    def get_state(self):
        return self.from_client, self.content, self.timestamp

    def set_state(self, state):
        self.from_client, self.content, self.timestamp = state

    def __repr__(self):
        return "{direction} {content}".format(
            direction="->" if self.from_client else "<-",
            content=repr(self.content)
        )


class TCPFlow(flow.Flow):

    """
    A TCPFlow is a simplified representation of a TCP session.
    """

    def __init__(self, client_conn, server_conn, live=None, index=0):
        super().__init__("tcp", client_conn, server_conn, live)
        self._messages =  dict() 
        self._message_order = list()
        self.index = index

    _stateobject_attributes = flow.Flow._stateobject_attributes.copy()
    _stateobject_attributes["messages"] = List[TCPMessage]

    def new_message(self, message):
        self._messages[message.id] = message
        self._message_order.append(message.id)

    @property
    def messages(self):
        return list(map(lambda entry: self._messages[entry], self._message_order)) 

    def get_message_by_id(self, message_id):
        return self._messages[message_id]

    def get_message_index(self, message_id):
        return self._message_order.index(message_id)

    def get_message_by_index(self, index):
        return self._messages[self._message_order[index]]

    def __repr__(self):
        return "<TCPFlow ({} messages)>".format(len(self.messages))

    @property
    def raw_content(self):
        raw = bytes()
        for message in self.messages:
           raw += message.raw_content
        return raw 

    @property
    def content(self):
        content = bytes()
        for message in self.messages:
           content += message.content
        return content


class TCPViewEntry(flow.Flow):
    def __init__(self, flow=None, message_id=None):
        self.flow = flow
        self.message_id = message_id
        self.id = str(uuid.uuid4())

    @property
    def client_stream(self):
        messages = list(filter(lambda message: message.from_client == True, self.messages))
        return TCPStream(self.client_conn, self.server_conn, messages)

    @property
    def server_stream(self):
        messages = list(filter(lambda message: message.from_client == False, self.messages))
        return TCPStream(self.client_conn, self.server_conn, messages)

    @property
    def direction(self):
        direction = self.message.from_client
        return "-->" if direction else "<--"
    @property
    def client(self):
        return human.format_address(self.client_conn.address)
    @property
    def server(self):
        return human.format_address(self.server_conn.address)

    @property
    def duration(self):
        index = self.message_index
        if index == 0:
            return 0
        else:
            prev = self.flow.get_message_by_index(index-1).timestamp
            current = self.message.timestamp
            return current-prev
    @property
    def messages(self):
        return self.flow.messages 

    @property
    def stream_index(self):
        return self.flow.index

    @property
    def message_index(self):
        return self.flow.get_message_index(self.message_id)

    @property
    def message(self):
        return self.flow.get_message_by_id(self.message_id)

    @property
    def timestamp(self):
        return self.message.timestamp

    @property
    def type(self):
        return self.flow.type

    @property
    def client_conn(self):
        return self.flow.client_conn

    @property
    def server_conn(self):
        return self.flow.server_conn

    @property
    def live(self):
        return self.flow.live

    @property
    def error(self):
        return self.flow.error

    @property
    def intercepted(self):
        return self.flow.intercepted

    @property
    def _backup(self):
        return self.flow._backup

    @property
    def reply(self):
        return self.flow.reply

    @property
    def marked(self):
        return self.flow.marked

    @property
    def metadata(self):
        return self.flow.metadata
 
    def get_state(self):
        return self.flow.get_state()

    def set_state(self, state):
        self.flow.set_state(state)

    def copy(self):
        return self.flow.copy()

    def modified(self):
        return self.modified()

    def backup(self, force=False):
        self.flow.backup(force)

    def revert(self):
        self.flow.revert()

    @property
    def killable(self):
        return self.flow.killable()

    def kill(self):
        self.flow.kill()

    def intercept(self):
        self.flow.intercept()

    def resume(self):
        self.flow.resume()

    def __repr__(self):
        return "<TCPViewEntry ({} messages)>".format(len(self.messages))


class TCPStream(TCPFlow):
    def __init__(self, client_conn, server_conn, messages):
        self.client_conn = client_conn
        self.server_conn = server_conn
        self._messages: List[TCPMessage] = messages

    @property
    def messages(self):
        return self._messages

    def get_message_by_id(self, message_id):
        raise NotImplemented

    def get_message_index(self, message_id):
        raise NotImplemented

    def get_message_by_index(self, index):
        return self.messages[index]
