import pytest

from mitmproxy.addons.maplocal import MapLocal, file_candidates
from mitmproxy.test import taddons
from mitmproxy.test import tflow

from mitmproxy.addons.modifyheaders import parse_modify_spec


@pytest.mark.parametrize(
    "url,spec,expected_candidates", [
        (
            "https://example.org/img/topic/subtopic/test.jpg",
            ":example.com/foo:/tmp",
            ["/tmp/img/topic/subtopic/test.jpg", "/tmp/img/topic/test.jpg", "/tmp/img/test.jpg", "/tmp/test.jpg"]
        ),
        (
            "https://example.org/img/topic/subtopic/",
            ":/img:/tmp",
            ["/tmp/img/topic/subtopic/index.html", "/tmp/img/topic/index.html", "/tmp/img/index.html", "/tmp/index.html"]
        ),
        (
            "https://example.org",
            ":org:/tmp",
            ["/tmp/index.html"]
        ),
    ]
)
def test_file_candidates(url, spec, expected_candidates):
    spec = parse_modify_spec(spec, True, True)
    candidates = file_candidates(url, spec.replacement)
    assert [str(x) for x in candidates] == expected_candidates


class TestMapLocal:
    def test_map_local(self, tmpdir):
        ml = MapLocal()

        with taddons.context(ml) as tctx:
            tmpfile = tmpdir.join("test1.jpg")
            tmpfile.write("foo")
            tctx.configure(
                ml,
                map_local=[
                    ":jpg:" + str(tmpdir)
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test1.jpg"
            ml.request(f)
            assert f.response.content == b"foo"

            tmpfile = tmpdir.join("images", "test2.jpg")
            tmpfile.write("bar", ensure=True)
            tctx.configure(
                ml,
                map_local=[
                    ":jpg:" + str(tmpdir)
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test2.jpg"
            ml.request(f)
            assert f.response.content == b"bar"

            tmpfile = tmpdir.join("images", "test3.jpg")
            tmpfile.write("foobar", ensure=True)
            tctx.configure(
                ml,
                map_local=[
                    ":jpg:" + str(tmpfile)
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/foo.jpg"
            ml.request(f)
            assert f.response.content == b"foobar"
