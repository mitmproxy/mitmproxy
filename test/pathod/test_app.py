import tutils


class TestApp(tutils.DaemonTests):
    SSL = False

    def test_index(self):
        r = self.getpath("/")
        assert r.status_code == 200
        assert r.content

    def test_about(self):
        r = self.getpath("/about")
        assert r.ok

    def test_download(self):
        r = self.getpath("/download")
        assert r.ok

    def test_docs(self):
        assert self.getpath("/docs/pathod").status_code == 200
        assert self.getpath("/docs/pathoc").status_code == 200
        assert self.getpath("/docs/language").status_code == 200
        assert self.getpath("/docs/pathod").status_code == 200
        assert self.getpath("/docs/test").status_code == 200

    def test_log(self):
        assert self.getpath("/log").status_code == 200
        assert self.get("200:da").status_code == 200
        id = self.d.log()[0]["id"]
        assert self.getpath("/log").status_code == 200
        assert self.getpath("/log/%s" % id).status_code == 200
        assert self.getpath("/log/9999999").status_code == 404

    def test_log_binary(self):
        assert self.get("200:h@10b=@10b:da")

    def test_response_preview(self):
        r = self.getpath("/response_preview", params=dict(spec="200"))
        assert r.status_code == 200
        assert 'Response' in r.content

        r = self.getpath("/response_preview", params=dict(spec="foo"))
        assert r.status_code == 200
        assert 'Error' in r.content

        r = self.getpath("/response_preview", params=dict(spec="200:b@100m"))
        assert r.status_code == 200
        assert "too large" in r.content

        r = self.getpath("/response_preview", params=dict(spec="200:b@5k"))
        assert r.status_code == 200
        assert 'Response' in r.content

        r = self.getpath(
            "/response_preview",
            params=dict(
                spec="200:b<nonexistent"))
        assert r.status_code == 200
        assert 'File access denied' in r.content

        r = self.getpath("/response_preview", params=dict(spec="200:b<file"))
        assert r.status_code == 200
        assert 'testfile' in r.content

    def test_request_preview(self):
        r = self.getpath("/request_preview", params=dict(spec="get:/"))
        assert r.status_code == 200
        assert 'Request' in r.content

        r = self.getpath("/request_preview", params=dict(spec="foo"))
        assert r.status_code == 200
        assert 'Error' in r.content

        r = self.getpath("/request_preview", params=dict(spec="get:/:b@100m"))
        assert r.status_code == 200
        assert "too large" in r.content

        r = self.getpath("/request_preview", params=dict(spec="get:/:b@5k"))
        assert r.status_code == 200
        assert 'Request' in r.content

        r = self.getpath("/request_preview", params=dict(spec=""))
        assert r.status_code == 200
        assert 'empty spec' in r.content
