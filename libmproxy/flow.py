"""
    This module provides more sophisticated flow tracking. These match requests
    with their responses, and provide filtering and interception facilities.
"""
import subprocess, base64, sys
from contrib import bson
import proxy, threading

class RunException(Exception):
    def __init__(self, msg, returncode, errout):
        Exception.__init__(self, msg)
        self.returncode = returncode
        self.errout = errout


class ReplayConnection:
    pass


# begin nocover
class ReplayThread(threading.Thread):
    def __init__(self, flow, masterq):
        self.flow, self.masterq = flow, masterq
        threading.Thread.__init__(self)

    def run(self):
        try:
            server = proxy.ServerConnection(self.flow.request)
            response = server.read_response()
            response.send(self.masterq)
        except proxy.ProxyError, v:
            err = proxy.Error(self.flow.connection, v.msg)
            err.send(self.masterq)
# end nocover


class Flow:
    def __init__(self, connection):
        self.connection = connection
        self.request, self.response, self.error = None, None, None
        self.intercepting = False
        self._backup = None

    def script_serialize(self):
        data = self.get_state()
        data = bson.dumps(data)
        return base64.encodestring(data)

    @classmethod
    def script_deserialize(klass, data):
        try:
            data = base64.decodestring(data)
            data = bson.loads(data)
        # bson.loads doesn't define a particular exception on error...
        except Exception:
            return None
        return klass.from_state(data)

    def run_script(self, path):
        """
            Run a script on a flow.

            Returns a (flow, stderr output) tuple, or raises RunException if
            there's an error.
        """
        self.backup()
        data = self.script_serialize()
        try:
            p = subprocess.Popen(
                    [path],
                    stdout=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
        except OSError, e:
            raise RunException(e.args[1], None, None)
        so, se = p.communicate(data)
        if p.returncode:
            raise RunException(
                "Script returned error code %s"%p.returncode,
                p.returncode,
                se
            )
        f = Flow.script_deserialize(so)
        if not f:
            raise RunException(
                    "Invalid response from script.",
                    p.returncode,
                    se
                )
        return f, se

    def dump(self):
        data = dict(
                flows = [self.get_state()]
               )
        return bson.dumps(data)

    def get_state(self):
        return dict(
            request = self.request.get_state() if self.request else None,
            response = self.response.get_state() if self.response else None,
            error = self.error.get_state() if self.error else None,
        )

    def load_state(self, state):
        if state["request"]:
            self.request = proxy.Request.from_state(state["request"])
        if state["response"]:
            self.response = proxy.Response.from_state(self.request, state["response"])
        if state["error"]:
            self.error = proxy.Error.from_state(state["error"])

    @classmethod
    def from_state(klass, state):
        f = klass(None)
        f.load_state(state)
        return f

    def __eq__(self, other):
        return self.get_state() == other.get_state()

    def modified(self):
        # FIXME: Save a serialization in backup, compare current with
        # backup to detect if flow has _really_ been modified.
        if self._backup:
            return True
        else:
            return False

    def backup(self):
        if not self._backup:
            self._backup = [
                self.connection.copy() if self.connection else None,
                self.request.copy() if self.request else None,
                self.response.copy() if self.response else None,
                self.error.copy() if self.error else None,
            ]

    def revert(self):
        if self._backup:
            restore = [i.copy() if i else None for i in self._backup]
            self.connection, self.request, self.response, self.error = restore
            self._backup = None

    def match(self, pattern):
        if pattern:
            if self.response:
                return pattern(self.response)
            elif self.request:
                return pattern(self.request)
        return False

    def is_replay(self):
        return isinstance(self.connection, ReplayConnection)

    def kill(self):
        if self.request and not self.request.acked:
            self.request.kill = True
            self.request.ack()
        elif self.response and not self.response.acked:
            self.response.kill = True
            self.response.ack()
        self.intercepting = False

    def intercept(self):
        self.intercepting = True

    def accept_intercept(self):
        if self.request:
            if not self.request.acked:
                self.request.ack()
            elif self.response and not self.response.acked:
                self.response.ack()
            self.intercepting = False


class State:
    def __init__(self):
        self.flow_map = {}
        self.flow_list = []
        # These are compiled filt expressions:
        self.limit = None
        self.intercept = None

    def add_browserconnect(self, f):
        """
            Start a browser connection.
        """
        self.flow_list.insert(0, f)
        self.flow_map[f.connection] = f

    def add_request(self, req):
        """
            Add a request to the state. Returns the matching flow.
        """
        f = self.flow_map.get(req.connection)
        if not f:
            return False
        f.request = req
        return f

    def add_response(self, resp):
        """
            Add a response to the state. Returns the matching flow.
        """
        f = self.flow_map.get(resp.request.connection)
        if not f:
            return False
        f.response = resp
        return f

    def add_error(self, err):
        """
            Add an error response to the state. Returns the matching flow, or
            None if there isn't one.
        """
        f = self.flow_map.get(err.connection)
        if not f:
            return None
        f.error = err
        return f

    def dump_flows(self):
        data = dict(
                flows =[i.get_state() for i in self.view]
               )
        return bson.dumps(data)

    def load_flows(self, js):
        data = bson.loads(js)
        data = [Flow.from_state(i) for i in data["flows"]]
        self.flow_list.extend(data)

    def set_limit(self, limit):
        """
            Limit is a compiled filter expression, or None.
        """
        self.limit = limit

    @property
    def view(self):
        if self.limit:
            return tuple([i for i in self.flow_list if i.match(self.limit)])
        else:
            return tuple(self.flow_list[:])

    def get_connection(self, itm):
        if isinstance(itm, (proxy.BrowserConnection, ReplayConnection)):
            return itm
        elif hasattr(itm, "connection"):
            return itm.connection
        elif hasattr(itm, "request"):
            return itm.request.connection

    def lookup(self, itm):
        """
            Checks for matching connection, using a Flow, Replay Connection,
            BrowserConnection, Request, Response or Error object. Returns None
            if not found.
        """
        connection = self.get_connection(itm)
        return self.flow_map.get(connection)

    def delete_flow(self, f):
        if not f.intercepting:
            c = self.get_connection(f)
            if c in self.flow_map:
                del self.flow_map[c]
            self.flow_list.remove(f)
            return True
        return False

    def clear(self):
        for i in self.flow_list[:]:
            self.delete_flow(i)

    def accept_all(self):
        for i in self.flow_list[:]:
            i.accept_intercept()

    def kill_flow(self, f):
        f.kill()
        self.delete_flow(f)

    def revert(self, f):
        """
            Replaces the matching connection object with a ReplayConnection object.
        """
        conn = self.get_connection(f)
        if conn in self.flow_map:
            del self.flow_map[conn]
        f.revert()
        self.flow_map[f.connection] = f

    def replay(self, f, masterq):
        """
            Replaces the matching connection object with a ReplayConnection object.

            Returns None if successful, or error message if not.
        """
        #begin nocover
        if f.intercepting:
            return "Can't replay while intercepting..."
        if f.request:
            f.backup()
            conn = self.get_connection(f)
            if conn in self.flow_map:
                del self.flow_map[conn]
            rp = ReplayConnection()
            f.connection = rp
            f.request.connection = rp
            if f.request.content:
                f.request.headers["content-length"] = [str(len(f.request.content))]
            f.response = None
            f.error = None
            self.flow_map[rp] = f
            rt = ReplayThread(f, masterq)
            rt.start()
        #end nocover
