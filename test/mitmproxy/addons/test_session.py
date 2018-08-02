import sqlite3
import asyncio
import pytest
import os

from mitmproxy import ctx
from mitmproxy import http
from mitmproxy.test import tflow, tutils
from mitmproxy.test import taddons
from mitmproxy.addons import session
from mitmproxy.exceptions import SessionLoadException, CommandError
from mitmproxy.utils.data import pkg_data


class TestSession:

    @staticmethod
    def tft(*, method="GET", start=0):
        f = tflow.tflow()
        f.request.method = method
        f.request.timestamp_start = start
        return f

    @staticmethod
    def start_session(fp=None):
        s = session.Session()
        tctx = taddons.context()
        tctx.master.addons.add(s)
        tctx.options.session_path = None
        if fp:
            s._flush_period = fp
        s.running()
        return s

    def test_session_temporary(self):
        s = session.SessionDB()
        td = s.tempdir
        filename = os.path.join(td, 'tmp.sqlite')
        assert session.SessionDB.is_session_db(filename)
        assert os.path.isdir(td)
        del s
        assert not os.path.isdir(td)

    def test_session_not_valid(self, tdata):
        path = tdata.path('mitmproxy/data/') + '/test_snv.sqlite'
        if os.path.isfile(path):
            os.remove(path)
        with open(path, 'w') as handle:
            handle.write("Not valid data")
        with pytest.raises(SessionLoadException):
            session.SessionDB(path)
        os.remove(path)

    def test_session_new_persistent(self, tdata):
        path = tdata.path('mitmproxy/data/') + '/test_np.sqlite'
        if os.path.isfile(path):
            os.remove(path)
        session.SessionDB(path)
        assert session.SessionDB.is_session_db(path)
        os.remove(path)

    def test_session_load_existing(self, tdata):
        path = tdata.path('mitmproxy/data/') + '/test_le.sqlite'
        if os.path.isfile(path):
            os.remove(path)
        con = sqlite3.connect(path)
        script_path = pkg_data.path("io/sql/session_create.sql")
        qry = open(script_path, 'r').read()
        with con:
            con.executescript(qry)
            blob = b'blob_of_data'
            con.execute(f'INSERT INTO FLOW VALUES(1, "{blob}");')
        con.close()
        session.SessionDB(path)
        con = sqlite3.connect(path)
        with con:
            cur = con.cursor()
            cur.execute('SELECT * FROM FLOW;')
            rows = cur.fetchall()
            assert len(rows) == 1
        con.close()
        os.remove(path)

    def test_session_order_generators(self):
        s = session.Session()
        tf = tflow.tflow(resp=True)

        s.order = "time"
        assert s._generate_order(tf) == 946681200

        s.order = "method"
        assert s._generate_order(tf) == tf.request.method

        s.order = "url"
        assert s._generate_order(tf) == tf.request.url

        s.order = "size"
        assert s._generate_order(tf) == len(tf.request.raw_content) + len(tf.response.raw_content)

    def test_simple(self):
        s = session.Session()
        ctx.options = taddons.context()
        ctx.options.session_path = None
        s.running()
        f = self.tft(start=1)
        assert s.store_count() == 0
        s.request(f)
        assert s._view == [(1, f.id)]
        assert s.load_view([f.id]) == [f]
        assert s.load_view(['nonexistent']) == [None]

        s.error(f)
        s.response(f)
        s.intercept(f)
        s.resume(f)
        s.kill(f)

        # Verify that flow has been updated, not duplicated
        assert s._view == [(1, f.id)]
        assert s.store_count() == 1

        f2 = self.tft(start=3)
        s.request(f2)
        assert s._view == [(1, f.id), (3, f2.id)]
        s.request(f2)
        assert s._view == [(1, f.id), (3, f2.id)]

        f3 = self.tft(start=2)
        s.request(f3)
        assert s._view == [(1, f.id), (2, f3.id), (3, f2.id)]
        s.request(f3)
        assert s._view == [(1, f.id), (2, f3.id), (3, f2.id)]
        assert s.store_count() == 3

        s.clear_storage()
        assert len(s._view) == 0
        assert s.store_count() == 0

    def test_filter(self):
        s = self.start_session()
        s.request(self.tft(method="get"))
        s.request(self.tft(method="put"))
        s.request(self.tft(method="get"))
        s.request(self.tft(method="put"))
        assert len(s._view) == 4
        s.set_filter("~m get")
        assert [f.request.method for f in s.load_view()] == ["GET", "GET"]
        assert s.store_count() == 4
        with pytest.raises(CommandError):
            s.set_filter("~notafilter")
        s.set_filter(None)
        assert len(s._view) == 4

    @pytest.mark.asyncio
    async def test_flush_withspecials(self):
        s = self.start_session(fp=0.5)
        f = self.tft()
        s.request(f)
        await asyncio.sleep(2)
        assert len(s._hot_store) == 0
        assert all([lflow.__dict__ == flow.__dict__ for lflow, flow in list(zip(s.load_view(), [f]))])

        f.server_conn.via = tflow.tserver_conn()
        s.request(f)
        await asyncio.sleep(1)
        assert len(s._hot_store) == 0
        assert all([lflow.__dict__ == flow.__dict__ for lflow, flow in list(zip(s.load_view(), [f]))])

        flows = [self.tft() for _ in range(500)]
        s.update(flows)
        fp = s._flush_period
        fr = s._flush_rate
        await asyncio.sleep(0.6)
        assert s._flush_period < fp and s._flush_rate > fr

    @pytest.mark.asyncio
    async def test_bodies(self):
        # Need to test for configure
        # Need to test for set_order
        s = self.start_session(fp=0.5)
        f = self.tft()
        f2 = self.tft(start=1)
        f.request.content = b"A"*1001
        s.request(f)
        s.request(f2)
        await asyncio.sleep(1.0)
        content = s.db_store.con.execute(
            "SELECT type_id, content FROM body WHERE body.flow_id == (?);", [f.id]
        ).fetchall()[0]
        assert content == (1, b"A"*1001)
        assert s.db_store.body_ledger == {f.id}
        f.response = http.HTTPResponse.wrap(tutils.tresp(content=b"A"*1001))
        f2.response = http.HTTPResponse.wrap(tutils.tresp(content=b"A"*1001))
        # Content length is wrong for some reason -- quick fix
        f.response.headers['content-length'] = b"1001"
        f2.response.headers['content-length'] = b"1001"
        s.response(f)
        s.response(f2)
        await asyncio.sleep(1.0)
        rows = s.db_store.con.execute(
            "SELECT type_id, content FROM body WHERE body.flow_id == (?);", [f.id]
        ).fetchall()
        assert len(rows) == 1
        rows = s.db_store.con.execute(
            "SELECT type_id, content FROM body WHERE body.flow_id == (?);", [f2.id]
        ).fetchall()
        assert len(rows) == 1
        assert s.db_store.body_ledger == {f.id}
        assert all([lf.__dict__ == rf.__dict__ for lf, rf in list(zip(s.load_view(), [f, f2]))])
