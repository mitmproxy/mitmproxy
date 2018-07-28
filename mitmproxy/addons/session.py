import tempfile
import asyncio
import typing
import bisect
import shutil
import sqlite3
import os

from mitmproxy import types
from mitmproxy import http
from mitmproxy import ctx
from mitmproxy.exceptions import SessionLoadException
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

    def __init__(self, db_path=None):
        """
        Connect to an already existing database,
        or create a new one with optional path.
        :param db_path:
        """
        self.tempdir = None
        self.con = None
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

    def _load_session(self, path):
        if not self.is_session_db(path):
            raise SessionLoadException('Given path does not point to a valid Session')
        self.con = sqlite3.connect(path)

    def _create_session(self):
        script_path = pkg_data.path("io/sql/session_create.sql")
        qry = open(script_path, 'r').read()
        with self.con:
            self.con.executescript(qry)

    @staticmethod
    def is_session_db(path):
        """
        Check if database entered from user
        is a valid Session SQLite DB.
        :return: True if valid, False if invalid.
        """
        try:
            c = sqlite3.connect(f'file:{path}?mode=rw', uri=True)
            cursor = c.cursor()
            cursor.execute("SELECT NAME FROM sqlite_master WHERE type='table';")
            rows = cursor.fetchall()
            tables = [('flow',), ('body',), ('annotation',)]
            if all(elem in rows for elem in tables):
                c.close()
                return True
        except:
            if c:
                c.close()
        return False


orders = [
    ("t", "time"),
    ("m", "method"),
    ("u", "url"),
    ("z", "size")
]


class Session:
    def __init__(self):
        self.sdb = SessionDB(ctx.options.session_path)
        self._hot_store = []
        self._view = []
        self.order = orders[0]
        self._flush_period = 3.0
        self._flush_rate = 150

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

    def _generate_order(self, f: http.HTTPFlow) -> typing.Union[str, int, float]:
        o = self.order
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

    async def _writer(self):
        while True:
            await asyncio.sleep(self._flush_period)
            tof = []
            to_dump = min(self._flush_rate, len(self._hot_store))
            for _ in range(to_dump):
                tof.append(self._hot_store.pop())
            self.store(tof)

    def store(self, flows: typing.Sequence[http.HTTPFlow]):
        pass

    def running(self):
        pass

    def add(self, flows: typing.Sequence[http.HTTPFlow]) -> None:
        for f in flows:
            if f.id not in [f.id for f in self._hot_store] and f.id not in self.sdb:
                # Flow has to be filtered here before adding to view. Later
                o = self._generate_order(f)
                self._view.insert(bisect.bisect_left(KeyifyList(self._view, lambda x: x[0]), o), (o, f.id))
                self._hot_store.append(f)

    def update(self, flow):
        pass

    def request(self, f):
        self.add([f])

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
