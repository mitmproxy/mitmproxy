import collections
import tempfile
import asyncio
import typing
import bisect
import shutil
import sqlite3
import copy
import os

from mitmproxy import flowfilter
from mitmproxy import types
from mitmproxy import http
from mitmproxy import ctx
from mitmproxy.io import protobuf
from mitmproxy.exceptions import SessionLoadException, CommandError
from mitmproxy.utils.data import pkg_data


class KeyifyList(object):
    def __init__(self, inner, key):
        self.inner = inner
        self.key = key

    def __len__(self):
        return len(self.inner)

    def __getitem__(self, k):
        return self.key(self.inner[k])


# Could be implemented using async libraries
class SessionDB:
    """
    This class wraps connection to DB
    for Sessions and handles creation,
    retrieving and insertion in tables.
    """
    content_threshold = 1000
    type_mappings = {
        "body": {
            1: "request",
            2: "response"
        }
    }

    def __init__(self, db_path=None):
        """
        Connect to an already existing database,
        or create a new one with optional path.
        :param db_path:
        """
        self.live_components: typing.Dict[str, tuple] = {}
        self.tempdir: tempfile.TemporaryDirectory = None
        self.con: sqlite3.Connection = None
        # This is used for fast look-ups over bodies already dumped to database.
        # This permits to enforce one-to-one relationship between flow and body table.
        self.body_ledger: typing.Set[str] = set()
        self.id_ledger: typing.Set[str] = set()
        if db_path is not None and os.path.isfile(db_path):
            self._load_session(db_path)
        else:
            if db_path:
                path = db_path
            else:
                self.tempdir = tempfile.mkdtemp()
                path = os.path.join(self.tempdir, 'tmp.sqlite')
            self.con = sqlite3.connect(path)
            self._create_session()

    def __del__(self):
        if self.con:
            self.con.close()
        if self.tempdir:
            shutil.rmtree(self.tempdir)

    def __contains__(self, fid):
        return fid in self.id_ledger

    def __len__(self):
        return len(self.id_ledger)

    def _load_session(self, path):
        if not self.is_session_db(path):
            raise SessionLoadException('Given path does not point to a valid Session')
        self.con = sqlite3.connect(path)

    def _create_session(self):
        script_path = pkg_data.path("io/sql/session_create.sql")
        with open(script_path, 'r') as qry:
            self.con.executescript(qry.read())
        self.con.commit()

    @staticmethod
    def is_session_db(path):
        """
        Check if database entered from user
        is a valid Session SQLite DB.
        :return: True if valid, False if invalid.
        """
        c = None
        try:
            c = sqlite3.connect(f'file:{path}?mode=rw', uri=True)
            cursor = c.cursor()
            cursor.execute("SELECT NAME FROM sqlite_master WHERE type='table';")
            rows = cursor.fetchall()
            tables = [('flow',), ('body',), ('annotation',)]
            if all(elem in rows for elem in tables):
                c.close()
                return True
        except sqlite3.Error:
            if c:
                c.close()
        return False

    def _disassemble(self, flow):
        # Some live components of flows cannot be serialized, but they are needed to ensure correct functionality.
        # We solve this by keeping a list of tuples which "save" those components for each flow id, eventually
        # adding them back when needed.
        self.live_components[flow.id] = (
            flow.client_conn.wfile,
            flow.client_conn.rfile,
            flow.client_conn.reply,
            flow.server_conn.wfile,
            flow.server_conn.rfile,
            flow.server_conn.reply,
            (flow.server_conn.via.wfile, flow.server_conn.via.rfile,
             flow.server_conn.via.reply) if flow.server_conn.via else None,
            flow.reply
        )

    def _reassemble(self, flow):
        if flow.id in self.live_components:
            cwf, crf, crp, swf, srf, srp, via, rep = self.live_components[flow.id]
            flow.client_conn.wfile = cwf
            flow.client_conn.rfile = crf
            flow.client_conn.reply = crp
            flow.server_conn.wfile = swf
            flow.server_conn.rfile = srf
            flow.server_conn.reply = srp
            flow.reply = rep
            if via:
                flow.server_conn.via.rfile, flow.server_conn.via.wfile, flow.server_conn.via.reply = via
        return flow

    def store_flows(self, flows):
        body_buf = []
        flow_buf = []
        for flow in flows:
            self.id_ledger.add(flow.id)
            self._disassemble(flow)
            f = copy.copy(flow)
            f.request = copy.deepcopy(flow.request)
            if flow.response:
                f.response = copy.deepcopy(flow.response)
            f.id = flow.id
            if len(f.request.content) > self.content_threshold and f.id not in self.body_ledger:
                body_buf.append((f.id, 1, f.request.content))
                f.request.content = b""
                self.body_ledger.add(f.id)
            if f.response and f.id not in self.body_ledger:
                if len(f.response.content) > self.content_threshold:
                    body_buf.append((f.id, 2, f.response.content))
                    f.response.content = b""
            flow_buf.append((f.id, protobuf.dumps(f)))
        self.con.executemany("INSERT OR REPLACE INTO flow VALUES(?, ?);", flow_buf)
        if body_buf:
            self.con.executemany("INSERT INTO body (flow_id, type_id, content) VALUES(?, ?, ?);", body_buf)
        self.con.commit()

    def retrieve_flows(self, ids=None):
        flows = []
        with self.con as con:
            if not ids:
                sql = "SELECT f.content, b.type_id, b.content " \
                      "FROM flow f " \
                      "LEFT OUTER JOIN body b ON f.id = b.flow_id;"
                rows = con.execute(sql).fetchall()
            else:
                sql = "SELECT f.content, b.type_id, b.content " \
                      "FROM flow f " \
                      "LEFT OUTER JOIN body b ON f.id = b.flow_id " \
                      f"AND f.id IN ({','.join(['?' for _ in range(len(ids))])});"
                rows = con.execute(sql, ids).fetchall()
            for row in rows:
                flow = protobuf.loads(row[0])
                if row[1]:
                    typ = self.type_mappings["body"][row[1]]
                    if typ and row[2]:
                        setattr(getattr(flow, typ), "content", row[2])
                flow = self._reassemble(flow)
                flows.append(flow)
        return flows

    def clear(self):
        self.con.executescript("DELETE FROM body; DELETE FROM annotation; DELETE FROM flow;")


matchall = flowfilter.parse(".")

orders = [
    "time",
    "method",
    "url",
    "size"
]


class Session:

    _FP_RATE = 150
    _FP_DECREMENT = 0.9
    _FP_DEFAULT = 3.0

    def __init__(self):
        self.db_store: SessionDB = None
        self._hot_store: collections.OrderedDict = collections.OrderedDict()
        self._order_store: typing.Dict[str, typing.Dict[str, typing.Union[int, float, str, None]]] = {}
        self._view: typing.List[typing.Tuple[typing.Union[int, float, str, None], str]] = []
        self.order: str = orders[0]
        self.filter = matchall
        self._flush_period: float = self._FP_DEFAULT
        self._flush_rate: int = self._FP_RATE
        self.started: bool = False

    def load(self, loader):
        loader.add_option(
            "session_path", typing.Optional[types.Path], None,
            "Path of session to load or to create."
        )
        loader.add_option(
            "view_order", str, "time",
            "Flow sort order.",
            choices=list(map(lambda c: c[1], orders))
        )
        loader.add_option(
            "view_filter", typing.Optional[str], None,
            "Limit the view to matching flows."
        )

    def running(self):
        if not self.started:
            self.started = True
            self.db_store = SessionDB(ctx.options.session_path)
            loop = asyncio.get_event_loop()
            loop.create_task(self._writer())

    def configure(self, updated):
        if "view_order" in updated:
            self.set_order(ctx.options.view_order)
        if "view_filter" in updated:
            self.set_filter(ctx.options.view_filter)

    async def _writer(self):
        while True:
            await asyncio.sleep(self._flush_period)
            batches = -(-len(self._hot_store) // self._flush_rate)
            self._flush_period = self._flush_period * self._FP_DECREMENT if batches > 1 else self._FP_DEFAULT
            while batches:
                tof = []
                to_dump = min(len(self._hot_store), self._flush_rate)
                for _ in range(to_dump):
                    tof.append(self._hot_store.popitem(last=False)[1])
                self.db_store.store_flows(tof)
                batches -= 1
                await asyncio.sleep(0.01)

    def load_view(self) -> typing.Sequence[http.HTTPFlow]:
        ids = [fid for _, fid in self._view]
        flows = self.load_storage(ids)
        return sorted(flows, key=lambda f: self._generate_order(self.order, f))

    def load_storage(self, ids=None) -> typing.Sequence[http.HTTPFlow]:
        flows = []
        ids_from_store = []
        if ids is not None:
            for fid in ids:
                # A same flow could be at the same time in hot and db storage. We want the most updated version.
                if fid in self._hot_store:
                    flows.append(self._hot_store[fid])
                elif fid in self.db_store:
                    ids_from_store.append(fid)
            flows += self.db_store.retrieve_flows(ids_from_store)
        else:
            for flow in self._hot_store.values():
                flows.append(flow)
            for flow in self.db_store.retrieve_flows():
                if flow.id not in self._hot_store:
                    flows.append(flow)
        return flows

    def clear_storage(self):
        self.db_store.clear()
        self._hot_store.clear()
        self._view = []

    def store_count(self) -> int:
        ln = 0
        for fid in self._hot_store.keys():
            if fid not in self.db_store:
                ln += 1
        return ln + len(self.db_store)

    @staticmethod
    def _generate_order(o: str, f: http.HTTPFlow) -> typing.Optional[typing.Union[str, int, float]]:
        if o == "time":
            return f.request.timestamp_start or 0
        if o == "method":
            return f.request.method
        if o == "url":
            return f.request.url
        if o == "size":
            s = 0
            if f.request.raw_content:
                s += len(f.request.raw_content)
            if f.response and f.response.raw_content:
                s += len(f.response.raw_content)
            return s
        return None

    def _store_order(self, f: http.HTTPFlow):
        self._order_store[f.id] = {}
        for order in orders:
            self._order_store[f.id][order] = self._generate_order(order, f)

    def set_order(self, order: str) -> None:
        if order not in orders:
            raise CommandError(
                "Unknown flow order: %s" % order
            )
        if order != self.order:
            self.order = order
            newview = [
                (self._order_store[t[1]][order], t[1]) for t in self._view
            ]
            self._view = sorted(newview)

    def _refilter(self):
        self._view = []
        flows = self.load_storage()
        for f in flows:
            if self.filter(f):
                self.update_view(f)

    def set_filter(self, input_filter: typing.Optional[str]) -> None:
        filt = matchall if not input_filter else flowfilter.parse(input_filter)
        if not filt:
            raise CommandError(
                "Invalid interception filter: %s" % filt
            )
        self.filter = filt
        self._refilter()

    def update_view(self, f):
        if any([f.id == t[1] for t in self._view]):
            self._view = [(order, fid) for order, fid in self._view if fid != f.id]
        o = self._order_store[f.id][self.order]
        self._view.insert(bisect.bisect_left(KeyifyList(self._view, lambda x: x[0]), o), (o, f.id))

    def update(self, flows: typing.Sequence[http.HTTPFlow]) -> None:
        for f in flows:
            self._store_order(f)
            if f.id in self._hot_store:
                self._hot_store.pop(f.id)
            self._hot_store[f.id] = f
            if self.filter(f):
                self.update_view(f)

    def request(self, f):
        self.update([f])

    def error(self, f):
        self.update([f])

    def response(self, f):
        self.update([f])

    def intercept(self, f):
        self.update([f])

    def resume(self, f):
        self.update([f])

    def kill(self, f):
        self.update([f])
