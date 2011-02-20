"""
    This module provides more sophisticated flow tracking. These match requests
    with their responses, and provide filtering and interception facilities.
"""
import subprocess, base64, sys, json, hashlib
import proxy, threading, netstring
import controller

class RunException(Exception):
    def __init__(self, msg, returncode, errout):
        Exception.__init__(self, msg)
        self.returncode = returncode
        self.errout = errout


# begin nocover
class RequestReplayThread(threading.Thread):
    def __init__(self, flow, masterq):
        self.flow, self.masterq = flow, masterq
        threading.Thread.__init__(self)

    def run(self):
        try:
            server = proxy.ServerConnection(self.flow.request)
            server.send_request(self.flow.request)
            response = server.read_response()
            response.send(self.masterq)
        except proxy.ProxyError, v:
            err = proxy.Error(self.flow.client_conn, v.msg)
            err.send(self.masterq)
# end nocover


class ServerPlaybackState:
    def __init__(self):
        self.fmap = {}

    def count(self):
        return sum([len(i) for i in self.fmap.values()])
    
    def load(self, flows):
        """
            Load a sequence of flows. We assume that the sequence is in
            chronological order.
        """
        for i in flows:
            if i.response:
                h = self._hash(i)
                l = self.fmap.setdefault(self._hash(i), [])
                l.append(i)

    def _hash(self, flow):
        """
            Calculates a loose hash of the flow request. 
        """
        r = flow.request
        key = [
            str(r.host),
            str(r.port),
            str(r.scheme),
            str(r.method),
            str(r.path),
            str(r.content),
        ]
        return hashlib.sha256(repr(key)).digest()

    def next_flow(self, request):
        """
            Returns the next flow object, or None if no matching flow was
            found.
        """
        l = self.fmap.get(self._hash(request))
        if not l:
            return None
        return l.pop(0)


class Flow:
    def __init__(self, request):
        self.request = request
        self.response, self.error = None, None
        self.intercepting = False
        self._backup = None

    def script_serialize(self):
        data = self.get_state()
        return json.dumps(data)

    @classmethod
    def script_deserialize(klass, data):
        try:
            data = json.loads(data)
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
        self.load_state(f.get_state())
        return se

    def get_state(self, nobackup=False):
        d = dict(
            request = self.request.get_state() if self.request else None,
            response = self.response.get_state() if self.response else None,
            error = self.error.get_state() if self.error else None,
        )
        if nobackup:
            d["backup"] = None
        else:
            d["backup"] = self._backup
        return d

    def load_state(self, state):
        self._backup = state["backup"]
        if self.request:
            self.request.load_state(state["request"])
        else:
            self.request = proxy.Request.from_state(state["request"])

        if state["response"]:
            if self.response:
                self.response.load_state(state["response"])
            else:
                self.response = proxy.Response.from_state(self.request, state["response"])
        else:
            self.response = None

        if state["error"]:
            if self.error:
                self.error.load_state(state["error"])
            else:
                self.error = proxy.Error.from_state(state["error"])
        else:
            self.error = None

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
        self._backup = self.get_state(nobackup=True)

    def revert(self):
        if self._backup:
            self.load_state(self._backup)
            self._backup = None

    def match(self, pattern):
        if pattern:
            if self.response:
                return pattern(self.response)
            elif self.request:
                return pattern(self.request)
        return False

    def kill(self):
        if self.request and not self.request.acked:
            self.request.ack(None)
        elif self.response and not self.response.acked:
            self.response.ack(None)
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
        self.client_connections = []
        self.flow_map = {}
        self.flow_list = []

        # These are compiled filt expressions:
        self.limit = None
        self.intercept = None

    def clientconnect(self, cc):
        self.client_connections.append(cc)

    def clientdisconnect(self, dc):
        """
            Start a browser connection.
        """
        self.client_connections.remove(dc.client_conn)

    def add_request(self, req):
        """
            Add a request to the state. Returns the matching flow.
        """
        f = Flow(req)
        self.flow_list.insert(0, f)
        self.flow_map[req] = f
        return f

    def add_response(self, resp):
        """
            Add a response to the state. Returns the matching flow.
        """
        f = self.flow_map.get(resp.request)
        if not f:
            return False
        f.response = resp
        return f

    def add_error(self, err):
        """
            Add an error response to the state. Returns the matching flow, or
            None if there isn't one.
        """
        f = self.flow_map.get(err.request) if err.request else None
        if not f:
            return None
        f.error = err
        return f

    def load_flows(self, flows):
        self.flow_list.extend(flows)
        for i in flows:
            self.flow_map[i.request] = i

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

    def delete_flow(self, f):
        if not f.intercepting:
            if f.request in self.flow_map:
                del self.flow_map[f.request]
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
        f.revert()

    def replay_request(self, f, masterq):
        """
            Returns None if successful, or error message if not.
        """
        #begin nocover
        if f.intercepting:
            return "Can't replay while intercepting..."
        if f.request:
            f.backup()
            f.request.set_replay()
            if f.request.content:
                f.request.headers["content-length"] = [str(len(f.request.content))]
            f.response = None
            f.error = None
            rt = RequestReplayThread(f, masterq)
            rt.start()
        #end nocover


class FlowMaster(controller.Master):
    def __init__(self, server, state):
        controller.Master.__init__(self, server)
        self.state = state
        self.playback = None
        self.scripts = {}
        self.kill_nonreplay = False

    def _runscript(self, f, script):
        return f.run_script(script)

    def set_response_script(self, s):
        self.scripts["response"] = s

    def set_request_script(self, s):
        self.scripts["request"] = s

    def start_playback(self, flows, kill):
        """
            flows: A list of flows.
            kill: Boolean, should we kill requests not part of the replay?
        """
        self.playback = ServerPlaybackState()
        self.playback.load(flows)
        self.kill_nonreplay = kill

    def do_playback(self, flow):
        """
            This method should be called by child classes in the handle_request
            handler. Returns True if playback has taken place, None if not.
        """
        if self.playback:
            rflow = self.playback.next_flow(flow)
            if not rflow:
                return None
            response = proxy.Response.from_state(flow.request, rflow.response.get_state())
            response.set_replay()
            flow.response = response
            flow.request.ack(response)
            return True
        return None

    def handle_clientconnect(self, r):
        self.state.clientconnect(r)
        r.ack()

    def handle_clientdisconnect(self, r):
        self.state.clientdisconnect(r)
        r.ack()

    def handle_error(self, r):
        f = self.state.add_error(r)
        r.ack()
        return f

    def handle_request(self, r):
        f = self.state.add_request(r)
        if "request" in self.scripts:
            self._runscript(f, self.scripts["request"])
        if self.playback:
            pb = self.do_playback(f)
            if not pb:
                if self.kill_nonreplay:
                    self.state.kill_flow(f)
                else:
                    r.ack()
        return f

    def handle_response(self, r):
        f = self.state.add_response(r)
        if not f:
            r.ack()
        if "response" in self.scripts:
            self._runscript(f, self.scripts["response"])
        return f


class FlowWriter:
    def __init__(self, fo):
        self.fo = fo
        self.ns = netstring.FileEncoder(fo)

    def add(self, flow):
        d = flow.get_state()
        s = json.dumps(d)
        self.ns.write(s)


class FlowReader:
    def __init__(self, fo):
        self.fo = fo
        self.ns = netstring.decode_file(fo)

    def stream(self):
        """
            Yields Flow objects from the dump.
        """
        for i in self.ns:
            data = json.loads(i)
            yield Flow.from_state(data)

