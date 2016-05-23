import os

from .. import tnetstring
from ..exceptions import FlowReadException
from ..models import FLOW_TYPES
from .compat import migrate_flow


class FlowWriter:
    def __init__(self, fo):
        self.fo = fo

    def add(self, flow):
        d = flow.get_state()
        tnetstring.dump(d, self.fo)


class FilteredFlowWriter:
    def __init__(self, fo, filt):
        self.fo = fo
        self.filt = filt

    def add(self, f):
        if self.filt and not f.match(self.filt):
            return
        d = f.get_state()
        tnetstring.dump(d, self.fo)


class FlowReader:
    def __init__(self, fo):
        self.fo = fo

    def stream(self):
        """
            Yields Flow objects from the dump.
        """

        # There is a weird mingw bug that breaks .tell() when reading from stdin.
        try:
            self.fo.tell()
        except IOError:  # pragma: no cover
            can_tell = False
        else:
            can_tell = True

        off = 0
        try:
            while True:
                data = tnetstring.load(self.fo)
                try:
                    data = migrate_flow(data)
                except ValueError as e:
                    raise FlowReadException(str(e))
                if can_tell:
                    off = self.fo.tell()
                if data["type"] not in FLOW_TYPES:
                    raise FlowReadException("Unknown flow type: {}".format(data["type"]))
                yield FLOW_TYPES[data["type"]].from_state(data)
        except ValueError:
            # Error is due to EOF
            if can_tell and self.fo.tell() == off and self.fo.read() == '':
                return
            raise FlowReadException("Invalid data format.")


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
        raise FlowReadException(e.strerror)
    return flows
