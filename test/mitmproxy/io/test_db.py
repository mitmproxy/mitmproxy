from mitmproxy.io import db
from mitmproxy.test import tflow


class TestDB:

    def test_create(self, tdata):
        dh = db.DbHandler(db_path=tdata.path("mitmproxy/io/data") + "/tmp.sqlite")
        with dh._con as c:
            cur = c.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='FLOWS';")
            assert cur.fetchall() == [('FLOWS',)]

    def test_roundtrip(self, tdata):
        dh = db.DbHandler(db_path=tdata.path("mitmproxy/io/data") + "/tmp.sqlite", mode='write')
        flows = []
        for i in range(10):
            flows.append(tflow.tflow())
        dh.store(flows)
        dh = db.DbHandler(db_path=tdata.path("mitmproxy/io/data") + "/tmp.sqlite")
        with dh._con as c:
            cur = c.cursor()
            cur.execute("SELECT count(*) FROM FLOWS;")
            assert cur.fetchall()[0][0] == 10
        loaded_flows = dh.load()
        assert len(loaded_flows) == len(flows)
