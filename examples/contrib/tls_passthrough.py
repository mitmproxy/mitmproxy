"""
This addon allows conditional TLS Interception based on a user-defined strategy.

Example:

    > mitmdump -s tls_passthrough.py

    1. curl --proxy http://localhost:8080 https://example.com --insecure
    // works - we'll also see the contents in mitmproxy

    2. curl --proxy http://localhost:8080 https://example.com
    // fails with a certificate error, which we will also see in mitmproxy

    3. curl --proxy http://localhost:8080 https://example.com
    // works again, but mitmproxy does not intercept and we do *not* see the contents
"""

import collections
import logging
import random
from abc import ABC
from abc import abstractmethod
from enum import Enum

from mitmproxy import connection
from mitmproxy import ctx
from mitmproxy import tls
from mitmproxy.addonmanager import Loader
from mitmproxy.utils import human


class InterceptionResult(Enum):
    SUCCESS = 1
    FAILURE = 2
    SKIPPED = 3


class TlsStrategy(ABC):
    def __init__(self):
        # A server_address -> interception results mapping
        self.history = collections.defaultdict(lambda: collections.deque(maxlen=200))

    @abstractmethod
    def should_intercept(self, server_address: connection.Address) -> bool:
        raise NotImplementedError()

    def record_success(self, server_address):
        self.history[server_address].append(InterceptionResult.SUCCESS)

    def record_failure(self, server_address):
        self.history[server_address].append(InterceptionResult.FAILURE)

    def record_skipped(self, server_address):
        self.history[server_address].append(InterceptionResult.SKIPPED)


class ConservativeStrategy(TlsStrategy):
    """
    Conservative Interception Strategy - only intercept if there haven't been any failed attempts
    in the history.
    """

    def should_intercept(self, server_address: connection.Address) -> bool:
        return InterceptionResult.FAILURE not in self.history[server_address]


class ProbabilisticStrategy(TlsStrategy):
    """
    Fixed probability that we intercept a given connection.
    """

    def __init__(self, p: float):
        self.p = p
        super().__init__()

    def should_intercept(self, server_address: connection.Address) -> bool:
        return random.uniform(0, 1) < self.p


class MaybeTls:
    strategy: TlsStrategy

    def load(self, loader: Loader):
        loader.add_option(
            "tls_strategy",
            int,
            0,
            "TLS passthrough strategy. If set to 0, connections will be passed through after the first unsuccessful "
            "handshake. If set to 0 < p <= 100, connections with be passed through with probability p.",
        )

    def configure(self, updated):
        if "tls_strategy" not in updated:
            return
        if ctx.options.tls_strategy > 0:
            self.strategy = ProbabilisticStrategy(ctx.options.tls_strategy / 100)
        else:
            self.strategy = ConservativeStrategy()

    @staticmethod
    def get_addr(server: connection.Server):
        # .peername may be unset in upstream proxy mode, so we need a fallback.
        return server.peername or server.address

    def tls_clienthello(self, data: tls.ClientHelloData):
        server_address = self.get_addr(data.context.server)
        if not self.strategy.should_intercept(server_address):
            logging.info(f"TLS passthrough: {human.format_address(server_address)}.")
            data.ignore_connection = True
            self.strategy.record_skipped(server_address)

    def tls_established_client(self, data: tls.TlsData):
        server_address = self.get_addr(data.context.server)
        logging.info(
            f"TLS handshake successful: {human.format_address(server_address)}"
        )
        self.strategy.record_success(server_address)

    def tls_failed_client(self, data: tls.TlsData):
        server_address = self.get_addr(data.context.server)
        logging.info(f"TLS handshake failed: {human.format_address(server_address)}")
        self.strategy.record_failure(server_address)


addons = [MaybeTls()]
