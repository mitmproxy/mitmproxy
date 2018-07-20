import sqlite3
import os
import pytest

from mitmproxy.exceptions import SessionLoadException
from mitmproxy.addons import session
from mitmproxy.utils.data import pkg_data


class TestSession:
    def test_session_temporary(self, tdata):
        open('tmp.sqlite', 'w')
        s = session.SessionDB()
        assert session.SessionDB.is_session_db('tmp.sqlite')
        s.con.close()
        os.remove('tmp.sqlite')

    def test_session_not_valid(self, tdata):
        path = tdata.path('mitmproxy/data/') + '/test.sqlite'
        if os.path.isfile(path):
            os.remove(path)
        with open(path, 'w') as handle:
            handle.write("Not valid data")
        with pytest.raises(SessionLoadException):
            session.SessionDB(path)

    def test_session_new_persistent(self, tdata):
        path = tdata.path('mitmproxy/data/') + '/test.sqlite'
        if os.path.isfile(path):
            os.remove(path)
        session.SessionDB(path)
        assert session.SessionDB.is_session_db(path)

    def test_session_load_existing(self, tdata):
        path = tdata.path('mitmproxy/data/') + '/test.sqlite'
        if os.path.isfile(path):
            os.remove(path)
        con = sqlite3.connect(path)
        script_path = pkg_data.path("io/sql/session_create.sql")
        qry = open(script_path, 'r').read()
        with con:
            con.executescript(qry)
            blob = b'blob_of_data'
            con.execute(f'INSERT INTO FLOW VALUES(1, 1, 1, "{blob}");')
        con.close()
        session.SessionDB(path)
        con = sqlite3.connect(path)
        with con:
            cur = con.cursor()
            cur.execute('SELECT * FROM FLOW;')
            rows = cur.fetchall()
            assert len(rows) == 1
