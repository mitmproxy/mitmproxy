import os
from typing import Type, Iterable, Dict, Union, Any, cast  # noqa

from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import flowfilter
from mitmproxy import http
from mitmproxy import tcp
from mitmproxy import websocket

from mitmproxy.io import compat
from mitmproxy.io import tnetstring

FLOW_TYPES: Dict[str, Type[flow.Flow]] = dict(
    http=http.HTTPFlow,
    websocket=websocket.WebSocketFlow,
    tcp=tcp.TCPFlow,
)


class FlowWriter:
    def __init__(self, fo):
        self.fo = fo

    def add(self, flow):
        d = flow.get_state()
        tnetstring.dump(d, self.fo)


class FlowReader:
    def __init__(self, fo):
        self.fo = fo

    def stream(self) -> Iterable[flow.Flow]:
        """
            Yields Flow objects from the dump.
        """
        try:
            while True:
                # FIXME: This cast hides a lack of dynamic type checking
                loaded = cast(
                    Dict[Union[bytes, str], Any],
                    tnetstring.load(self.fo),
                )
                try:
                    mdata = compat.migrate_flow(loaded)
                except ValueError as e:
                    raise exceptions.FlowReadException(str(e))
                if mdata["type"] not in FLOW_TYPES:
                    raise exceptions.FlowReadException("Unknown flow type: {}".format(mdata["type"]))
                yield FLOW_TYPES[mdata["type"]].from_state(mdata)
        except ValueError as e:
            if str(e) == "not a tnetstring: empty file":
                return  # Error is due to EOF
            raise exceptions.FlowReadException("Invalid data format.")


class FilteredFlowWriter:
    def __init__(self, fo, flt):
        self.fo = fo
        self.flt = flt

    def add(self, f: flow.Flow):
        if self.flt and not flowfilter.match(self.flt, f):
            return
        d = f.get_state()
        tnetstring.dump(d, self.fo)


def read_flows_from_paths(paths):
    """
    Given a list of filepaths, read all flows and return a list of them.
    From a performance perspective, streaming would be advisable -
    however, if there's an error with one of the files, we want it to be raised immediately.

    Raises:
        FlowReadException, if any error occurs.
    """
    try:
        flows = []
        for path in paths:
            path = os.path.expanduser(path)
            with open(path, "rb") as f:
                flows.extend(FlowReader(f).stream())
    except IOError as e:
        raise exceptions.FlowReadException(e.strerror)
    return flows
