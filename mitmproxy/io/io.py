import bz2
import gzip
import json
import lzma
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

# Magic bytes for compressed formats
_GZIP_MAGIC = b"\x1f\x8b"
_BZ2_MAGIC = b"BZh"
_XZ_MAGIC = b"\xfd7zXZ\x00"


def open_flow_file(path: str) -> BinaryIO:
    """
    Open a flow file for reading, auto-detecting compression from magic bytes.
    """
    with open(path, "rb") as raw:
        header = raw.read(6)

    if header[:2] == _GZIP_MAGIC:
        return cast(BinaryIO, gzip.open(path, "rb"))
    elif header[:3] == _BZ2_MAGIC:
        return cast(BinaryIO, bz2.open(path, "rb"))
    elif header[:6] == _XZ_MAGIC:
        return cast(BinaryIO, lzma.open(path, "rb"))
    else:
        return open(path, "rb")


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
        try:
            yield from self._stream_inner()
        except (EOFError, OSError, lzma.LZMAError) as e:
            raise exceptions.FlowReadException(f"Invalid data format: {e}") from e

    def _stream_inner(self) -> Iterable[flow.Flow]:
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
    def __init__(self, fo: BinaryIO, flt: flowfilter.TFilter | None):
        self.fo = fo
        self.flt = flt

    def add(self, f: flow.Flow) -> None:
        if self.flt and not flowfilter.match(self.flt, f):
            return
        d = f.get_state()
        tnetstring.dump(d, self.fo)
        self.fo.flush()


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
            with open_flow_file(path) as f:
                flows.extend(FlowReader(f).stream())
    except OSError as e:
        raise exceptions.FlowReadException(e.strerror)
    except (EOFError, lzma.LZMAError) as e:
        raise exceptions.FlowReadException(f"Error reading compressed flow file: {e}")
    return flows
