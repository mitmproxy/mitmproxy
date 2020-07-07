import pytest
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
