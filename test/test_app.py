import tutils

class TestApp(tutils.DaemonTests):
    SSL = False
    def test_index(self):
        r = self.getpath("/")
        assert r.status_code == 200
        assert r.content

    def test_docs(self):
        assert self.getpath("/docs/pathod").status_code == 200
        assert self.getpath("/docs/pathoc").status_code == 200
        assert self.getpath("/docs/language").status_code == 200
        assert self.getpath("/docs/test").status_code == 200

    def test_log(self):
        assert self.getpath("/log").status_code == 200
        assert self.get("200").status_code == 200
        id = self.d.log()[0]["id"]
        assert self.getpath("/log").status_code == 200
        assert self.getpath("/log/%s"%id).status_code == 200
        assert self.getpath("/log/9999999").status_code == 404

    def test_preview(self):
        r = self.getpath("/preview", params=dict(spec="200"))
        assert r.status_code == 200
        assert 'Response' in r.content

        r = self.getpath("/preview", params=dict(spec="foo"))
        assert r.status_code == 200
        assert 'Error' in r.content

        r = self.getpath("/preview", params=dict(spec="200:b@100m"))
        assert r.status_code == 200
        assert "too large" in r.content

        r = self.getpath("/preview", params=dict(spec="200:b@5k"))
        assert r.status_code == 200
        assert 'Response' in r.content


