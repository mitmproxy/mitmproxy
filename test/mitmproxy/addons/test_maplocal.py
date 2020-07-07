from pathlib import Path

from mitmproxy.addons.maplocal import MapLocal
from mitmproxy.test import taddons
from mitmproxy.test import tflow

from mitmproxy.addons.modifyheaders import parse_modify_spec


class TestMapLocal:
    def test_file_candidates(self, tmpdir):
        ml = MapLocal()

        url = "https://example.org/img/topic/subtopic/test.jpg"
        spec = parse_modify_spec(":/img/jpg:" + str(tmpdir), True, True)
        file_candidates = ml.file_candidates(url, spec)
        assert file_candidates[0] == str(tmpdir) + "/img/topic/subtopic/test.jpg"
        assert file_candidates[1] == str(tmpdir) + "/img/topic/test.jpg"
        assert file_candidates[2] == str(tmpdir) + "/img/test.jpg"
        assert file_candidates[3] == str(tmpdir) + "/test.jpg"

        url = "https://example.org/img/topic/subtopic/"
        spec = parse_modify_spec(":/img:" + str(tmpdir), True, True)
        file_candidates = ml.file_candidates(url, spec)
        assert file_candidates[0] == str(tmpdir) + "/img/topic/subtopic/index.html"
        assert file_candidates[1] == str(tmpdir) + "/img/topic/index.html"
        assert file_candidates[2] == str(tmpdir) + "/img/index.html"
        assert file_candidates[3] == str(tmpdir) + "/index.html"

        url = "https://example.org"
        spec = parse_modify_spec(":org:" + str(tmpdir), True, True)
        file_candidates = ml.file_candidates(url, spec)
        assert file_candidates[0] == str(tmpdir) + "/index.html"

    def test_sanitize_candidate_path(self, tmpdir):
        base_dir = Path(str(tmpdir))

        tmpdir.join("testdir1", "testdir2", "testdir3", "testdir4", "testfile").write("bar", ensure=True)

        ml = MapLocal()
        assert ml.sanitize_candidate_path(
            base_dir.joinpath("..", "bar"), base_dir
        ) is None
        assert ml.sanitize_candidate_path(
            base_dir.joinpath(".."), base_dir
        ) is None
        assert ml.sanitize_candidate_path(
            base_dir.joinpath("..", ".."), base_dir
        ) is None
        assert ml.sanitize_candidate_path(
            base_dir.joinpath("..", "..", "..", "..", "..", "..", "etc", "passwd"), base_dir
        ) is None

        assert ml.sanitize_candidate_path(
            base_dir.joinpath("testdir1"), base_dir
        ) is not None
        assert ml.sanitize_candidate_path(
            base_dir.joinpath("testdir1", "testdir2"), base_dir
        ) is not None
        assert ml.sanitize_candidate_path(
            base_dir.joinpath("testdir1", "testdir2", "testdir3", "testdir4", "testfile"), base_dir
        ) is not None
        assert ml.sanitize_candidate_path(
            base_dir.joinpath("testdir1", "testdir2", "testdir3", "testdir4", "testfile"),
            base_dir.joinpath("testdir1", "testdir2", "testdir3", "testdir4", "testfile")
        ) is not None

    def test_modify_headers(self, tmpdir):
        ml = MapLocal()

        with taddons.context(ml) as tctx:
            tmpfile = tmpdir.join("test1.jpg")
            tmpfile.write("local content 1")

            tctx.configure(
                ml,
                map_local=[
                    ":jpg:" + str(tmpdir)
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test1.jpg"
            ml.request(f)
            assert f.response.content == b"local content 1"

            tmpfile = tmpdir.join("images", "test2.jpg")
            tmpfile.write("local content 2", ensure=True)

            tctx.configure(
                ml,
                map_local=[
                    ":jpg:" + str(tmpdir)
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test2.jpg"
            ml.request(f)
            assert f.response.content == b"local content 2"

            tmpfile = tmpdir.join("images", "test3.jpg")
            tmpfile.write("local content 3", ensure=True)

            tctx.configure(
                ml,
                map_local=[
                    ":jpg:" + str(tmpfile)
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test3.jpg"
            ml.request(f)
            assert f.response.content == b"local content 3"
