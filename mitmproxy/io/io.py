import json
import os
from collections.abc import Iterable
from io import BufferedReader
from typing import Any
from typing import BinaryIO
from typing import cast
from typing import Union

from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import flowfilter
from mitmproxy.io import compat
from mitmproxy.io import tnetstring
from mitmproxy.io.har import request_to_flow


class FlowWriter:
    def __init__(self, fo):
        self.fo = fo

    def add(self, f: flow.Flow) -> None:
        d = f.get_state()
        tnetstring.dump(d, self.fo)


class FlowReader:
    fo: BinaryIO

    def __init__(self, fo: BinaryIO):
        self.fo = fo

    def peek(self, n: int) -> bytes:
        try:
            return cast(BufferedReader, self.fo).peek(n)
        except AttributeError:
            # https://github.com/python/cpython/issues/90533: io.BytesIO does not have peek()
            pos = self.fo.tell()
            ret = self.fo.read(n)
            self.fo.seek(pos)
            return ret

    def stream(self) -> Iterable[flow.Flow]:
        """
        Yields Flow objects from the dump.
        """

        if self.peek(4).startswith(
            b"\xef\xbb\xbf{"
        ):  # skip BOM, usually added by Fiddler
            self.fo.read(3)
        if self.peek(1).startswith(b"{"):
            try:
                har_file = json.loads(self.fo.read().decode("utf-8"))

                for request_json in har_file["log"]["entries"]:
                    yield request_to_flow(request_json)

            except Exception:
                raise exceptions.FlowReadException(
                    "Unable to read HAR file. Please provide a valid HAR file"
                )

        else:
            try:
                while True:
                    # FIXME: This cast hides a lack of dynamic type checking
                    loaded = cast(
                        dict[Union[bytes, str], Any],
                        tnetstring.load(self.fo),
                    )
                    try:
                        if not isinstance(loaded, dict):
                            raise ValueError(f"Invalid flow: {loaded=}")
                        yield flow.Flow.from_state(compat.migrate_flow(loaded))
                    except ValueError as e:
                        raise exceptions.FlowReadException(e) from e
            except (ValueError, TypeError, IndexError) as e:
                if str(e) == "not a tnetstring: empty file":
                    return  # Error is due to EOF
                raise exceptions.FlowReadException("Invalid data format.") from e


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
