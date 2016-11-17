from abc import ABCMeta, abstractmethod

from mitmproxy.proxy.protocol2.context import Context
from mitmproxy.proxy.protocol2.events import Event, TEventGenerator


class Layer(metaclass=ABCMeta):
    def __init__(self, context: Context) -> None:
        self.context = context

    @abstractmethod
    def handle_event(self, event: Event) -> TEventGenerator:
        if False:
            yield None
