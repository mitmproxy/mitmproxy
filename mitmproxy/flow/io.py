from __future__ import absolute_import, print_function, division

import os

from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import models
from mitmproxy.contrib import tnetstring
from mitmproxy.flow import io_compat


class FlowWriter:
    def __init__(self, fo):
        self.fo = fo

    def add(self, flow):
        d = flow.get_state()
        tnetstring.dump(d, self.fo)


class FlowReader:
    def __init__(self, fo):
        self.fo = fo

    def stream(self):
        """
            Yields Flow objects from the dump.
        """
        try:
            while True:
                data = tnetstring.load(self.fo)
                try:
                    data = io_compat.migrate_flow(data)
                except ValueError as e:
                    raise exceptions.FlowReadException(str(e))
                if data["type"] not in models.FLOW_TYPES:
                    raise exceptions.FlowReadException("Unknown flow type: {}".format(data["type"]))
                yield models.FLOW_TYPES[data["type"]].from_state(data)
        except ValueError as e:
            if str(e) == "not a tnetstring: empty file":
                return  # Error is due to EOF
            raise exceptions.FlowReadException("Invalid data format.")


class FilteredFlowWriter:
    def __init__(self, fo, flt):
        self.fo = fo
        self.flt = flt

    def add(self, flow):
        if self.flt and not flowfilter.match(self.flt, flow):
            return
        d = flow.get_state()
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
