import os
from typing import Any, BinaryIO, Iterable, Union, cast

from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import flowfilter
from mitmproxy.io import compat
from mitmproxy.io import tnetstring


class FlowWriter:
    def __init__(self, fo):
        self.fo = fo

    def add(self, f: flow.Flow) -> None:
        d = f.get_state()
        tnetstring.dump(d, self.fo)


class FlowReader:
    def __init__(self, fo: BinaryIO):
        self.fo: BinaryIO = fo

    def stream(self) -> Iterable[flow.Flow]:
        """
        Yields Flow objects from the dump.
        """
        try:
            while True:
                # FIXME: This cast hides a lack of dynamic type checking
                loaded = cast(
                    dict[Union[bytes, str], Any],
                    tnetstring.load(self.fo),
                )
                try:
                    yield flow.Flow.from_state(compat.migrate_flow(loaded))
                except ValueError as e:
                    raise exceptions.FlowReadException(e)
        except (ValueError, TypeError, IndexError) as e:
            if str(e) == "not a tnetstring: empty file":
                return  # Error is due to EOF
            raise exceptions.FlowReadException("Invalid data format.")


class FilteredFlowWriter:
    def __init__(self, fo, flt):
        self.fo = fo
        self.flt = flt

    def add(self, f: flow.Flow) -> None:
        if self.flt and not flowfilter.match(self.flt, f):
            return
        d = f.get_state()
        tnetstring.dump(d, self.fo)


def read_flows_from_paths(paths) -> list[flow.Flow]:
    """
    Given a list of filepaths, read all flows and return a list of them.
    From a performance perspective, streaming would be advisable -
    however, if there's an error with one of the files, we want it to be raised immediately.

    Raises:
        FlowReadException, if any error occurs.
    """
    try:
        flows: list[flow.Flow] = []
        for path in paths:
            path = os.path.expanduser(path)
            with open(path, "rb") as f:
                flows.extend(FlowReader(f).stream())
    except OSError as e:
        raise exceptions.FlowReadException(e.strerror)
    return flows
