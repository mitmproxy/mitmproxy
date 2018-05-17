import sqlite3


class DummySession:

    """
    Represent a session of mitmproxy.
    It basically wraps an SQLiteDB connection.
    Only barebone functionality here, so...dummy.
    """

    queries = {
        'create_table': 'CREATE TABLE DUMMY_SESSION (MID INTEGER PBUF BLOB)',
        'insert_into':  'INSERT INTO DUMMY_SESSION values (:mid, :pbuf_blob)',
        'select_w_mid':   'SELECT PBUF_BLOB FROM DUMMY_SESSION WHERE mid=:mid'
    }
    mid = 0

    def __init__(self, path='./tmp/mxsession.db'):
        if path is None:
            path = './tmp/mxsession.db'
            self.temp = True
        else:
            self.temp = False
        self._c = sqlite3.connect(path).cursor()
        if not self.temp:
            self._c.execute(self.queries['create_table'])

    def store(self, blob):
        if blob is not None:
            self._c.execute(self.queries['insert_into'], {'mid': self.mid, 'pbuf_blob': blob})
            self.mid += 1
        return self.mid

    def collect(self, mid):
        self._c.execute(self.queries['select_w_mid'], {'mid': mid})
        return self._c.fetchone()


