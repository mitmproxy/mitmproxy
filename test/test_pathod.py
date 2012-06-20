from libpathod import pathod

class _TestApplication:
    def test_anchors(self):
        a = pathod.PathodApp(staticdir=None)
        a.add_anchor("/foo", "200")
        assert a.get_anchors() == [("/foo", "200")]
        a.add_anchor("/bar", "400")
        assert a.get_anchors() == [("/bar", "400"), ("/foo", "200")]
        a.remove_anchor("/bar", "400")
        assert a.get_anchors() == [("/foo", "200")]
        a.remove_anchor("/oink", "400")
        assert a.get_anchors() == [("/foo", "200")]

    def test_logs(self):
        a = pathod.PathodApp(staticdir=None)
        a.LOGBUF = 3
        a.add_log({})
        assert a.log[0]["id"] == 0
        a.add_log({})
        a.add_log({})
        assert a.log[0]["id"] == 2
        a.add_log({})
        assert len(a.log) == 3
        assert a.log[0]["id"] == 3
        assert a.log[-1]["id"] == 1

        assert a.log_by_id(1)["id"] == 1
        assert not a.log_by_id(0)


class TestPathod:
    def test_instantiation(self):
        pathod.Pathod(("127.0.0.1", 0))
        
