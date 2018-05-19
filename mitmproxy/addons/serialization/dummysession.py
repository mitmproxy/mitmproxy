import os
import sqlite3

from mitmproxy.utils import data


class DummySession:

    """
    Represent a session of mitmproxy.
    It basically wraps an SQLiteDB connection.
    Only barebone functionality here, so...dummy.
    """

    queries = {
        'create_table': 'CREATE TABLE DUMMY_SESSION (MID INTEGER PRIMARY KEY, '
                        'PBUF_BLOB BLOB)',
        'insert_into':  'INSERT INTO DUMMY_SESSION values (:mid, :pbuf_blob)',
        'select_w_mid':   'SELECT PBUF_BLOB FROM DUMMY_SESSION WHERE mid=:mid'
    }
    mid = 0

    default_spath = data.pkg_data.path('addons/serialization') + '/mxsession.db'

    def __init__(self):
        if os.path.isfile(self.default_spath):
            os.remove(self.default_spath)
        self._con = sqlite3.connect(self.default_spath)
        self._c = self._con.cursor()
        self._create_session()

    def _create_session(self):
        with self._con:
            self._con.execute(self.queries['create_table'])

    def close(self):
        self._con.close()

    def store(self, blob):
        if blob is not None:
            with self._con:
                self._con.execute(self.queries['insert_into'], {'mid': self.mid, 'pbuf_blob': blob})
            self.mid += 1
        return self.mid - 1

    def collect(self, mid):
        self._c.execute(self.queries['select_w_mid'], {'mid': mid})
        return self._c.fetchone()[0]


