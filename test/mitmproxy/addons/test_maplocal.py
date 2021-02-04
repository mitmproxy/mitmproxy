import sys
from pathlib import Path

import pytest

from mitmproxy.addons.maplocal import MapLocal, MapLocalSpec, file_candidates
from mitmproxy.utils.spec import parse_spec
from mitmproxy.test import taddons
from mitmproxy.test import tflow


@pytest.mark.parametrize(
    "url,spec,expected_candidates",
    [
        # trailing slashes
        ("https://example.com/foo", ":example.com/foo:/tmp", ["/tmp/index.html"]),
        ("https://example.com/foo/", ":example.com/foo:/tmp", ["/tmp/index.html"]),
        ("https://example.com/foo", ":example.com/foo:/tmp/", ["/tmp/index.html"]),
    ] + [
        # simple prefixes
        ("http://example.com/foo/bar.jpg", ":example.com/foo:/tmp", ["/tmp/bar.jpg", "/tmp/bar.jpg/index.html"]),
        ("https://example.com/foo/bar.jpg", ":example.com/foo:/tmp", ["/tmp/bar.jpg", "/tmp/bar.jpg/index.html"]),
        ("https://example.com/foo/bar.jpg?query", ":example.com/foo:/tmp", ["/tmp/bar.jpg", "/tmp/bar.jpg/index.html"]),
        ("https://example.com/foo/bar/baz.jpg", ":example.com/foo:/tmp",
         ["/tmp/bar/baz.jpg", "/tmp/bar/baz.jpg/index.html"]),
        ("https://example.com/foo/bar.jpg", ":/foo/bar.jpg:/tmp", ["/tmp/index.html"]),
    ] + [
        # URL decode and special characters
        ("http://example.com/foo%20bar.jpg", ":example.com:/tmp", [
            "/tmp/foo bar.jpg",
            "/tmp/foo bar.jpg/index.html",
            "/tmp/foo_bar.jpg",
            "/tmp/foo_bar.jpg/index.html"
        ]),
        ("http://example.com/fóobår.jpg", ":example.com:/tmp", [
            "/tmp/fóobår.jpg",
            "/tmp/fóobår.jpg/index.html",
            "/tmp/f_ob_r.jpg",
            "/tmp/f_ob_r.jpg/index.html"
        ]),
    ] + [
        # index.html
        ("https://example.com/foo", ":example.com/foo:/tmp", ["/tmp/index.html"]),
        ("https://example.com/foo/", ":example.com/foo:/tmp", ["/tmp/index.html"]),
        ("https://example.com/foo/bar", ":example.com/foo:/tmp", ["/tmp/bar", "/tmp/bar/index.html"]),
        ("https://example.com/foo/bar/", ":example.com/foo:/tmp", ["/tmp/bar", "/tmp/bar/index.html"]),
    ] + [
        # regex
        (
                "https://example/view.php?f=foo.jpg",
                ":example/view.php\\?f=(.+):/tmp",
                ["/tmp/foo.jpg", "/tmp/foo.jpg/index.html"]
        ), (
                "https://example/results?id=1&foo=2",
                ":example/(results\\?id=.+):/tmp",
                [
                    "/tmp/results?id=1&foo=2",
                    "/tmp/results?id=1&foo=2/index.html",
                    "/tmp/results_id=1_foo=2",
                    "/tmp/results_id=1_foo=2/index.html"
                ]
        ),
    ] + [
        # test directory traversal detection
        ("https://example.com/../../../../../../etc/passwd", ":example.com:/tmp", []),
        # this is slightly hacky, but werkzeug's behavior differs per system.
        ("https://example.com/C:\\foo.txt", ":example.com:/tmp", [] if sys.platform == "win32" else [
            "/tmp/C:\\foo.txt",
            "/tmp/C:\\foo.txt/index.html",
            "/tmp/C__foo.txt",
            "/tmp/C__foo.txt/index.html"
        ]),
        ("https://example.com//etc/passwd", ":example.com:/tmp", ["/tmp/etc/passwd", "/tmp/etc/passwd/index.html"]),
    ]
)
def test_file_candidates(url, spec, expected_candidates):
    # we circumvent the path existence checks here to simplify testing
    filt, subj, repl = parse_spec(spec)
    spec = MapLocalSpec(filt, subj, Path(repl))

    candidates = file_candidates(url, spec)
    assert [x.as_posix() for x in candidates] == expected_candidates


class TestMapLocal:

    def test_configure(self, tmpdir):
        ml = MapLocal()
        with taddons.context(ml) as tctx:
            tctx.configure(ml, map_local=["/foo/bar/" + str(tmpdir)])
            with pytest.raises(Exception, match="Invalid regular expression"):
                tctx.configure(ml, map_local=["/foo/+/" + str(tmpdir)])
            with pytest.raises(Exception, match="Invalid file path"):
                tctx.configure(ml, map_local=["/foo/.+/three"])

    def test_simple(self, tmpdir):
        ml = MapLocal()

        with taddons.context(ml) as tctx:
            tmpfile = tmpdir.join("foo.jpg")
            tmpfile.write("foo")
            tctx.configure(
                ml,
                map_local=[
                    "|//example.org/images|" + str(tmpdir)
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/foo.jpg"
            ml.request(f)
            assert f.response.content == b"foo"

            tmpfile = tmpdir.join("images", "bar.jpg")
            tmpfile.write("bar", ensure=True)
            tctx.configure(
                ml,
                map_local=[
                    "|//example.org|" + str(tmpdir)
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/bar.jpg"
            ml.request(f)
            assert f.response.content == b"bar"

            tmpfile = tmpdir.join("foofoobar.jpg")
            tmpfile.write("foofoobar", ensure=True)
            tctx.configure(
                ml,
                map_local=[
                    "|example.org/foo/foo/bar.jpg|" + str(tmpfile)
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/foo/foo/bar.jpg"
            ml.request(f)
            assert f.response.content == b"foofoobar"

    @pytest.mark.asyncio
    async def test_nonexistent_files(self, tmpdir, monkeypatch):
        ml = MapLocal()

        with taddons.context(ml) as tctx:
            tctx.configure(
                ml,
                map_local=[
                    "|example.org/css|" + str(tmpdir)
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/css/nonexistent"
            ml.request(f)
            assert f.response.status_code == 404
            await tctx.master.await_log("None of the local file candidates exist")

            tmpfile = tmpdir.join("foo.jpg")
            tmpfile.write("foo")
            tctx.configure(
                ml,
                map_local=[
                    "|//example.org/images|" + str(tmpfile)
                ]
            )
            tmpfile.remove()
            monkeypatch.setattr(Path, "is_file", lambda x: True)
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/foo.jpg"
            ml.request(f)
            await tctx.master.await_log("could not read file")

    def test_has_reply(self, tmpdir):
        ml = MapLocal()
        with taddons.context(ml) as tctx:
            tmpfile = tmpdir.join("foo.jpg")
            tmpfile.write("foo")
            tctx.configure(
                ml,
                map_local=[
                    "|//example.org/images|" + str(tmpfile)
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/foo.jpg"
            f.reply.take()
            ml.request(f)
            assert not f.response
