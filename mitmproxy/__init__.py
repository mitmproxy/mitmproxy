from typing import Callable  # noqa
from mitmproxy import flow  # noqa

master = None  # type: flow.FlowMaster
log = None  # type: Callable[[str], None]
