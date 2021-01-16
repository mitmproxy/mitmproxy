import json
from json import JSONDecodeError
from pathlib import Path
from unittest import mock
from typing import List
from unittest.mock import patch

from mitmproxy.test import tflow
from mitmproxy.test import tutils

from examples.contrib.webscanner_helper.urlindex import UrlIndexWriter, SetEncoder, JSONUrlIndexWriter, \
    TextUrlIndexWriter, WRITER, \
    filter_404, \
    UrlIndexAddon


class TestBaseClass:

    @patch.multiple(UrlIndexWriter, __abstractmethods__=set())
    def test_base_class(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        index_writer = UrlIndexWriter(tmpfile)
        index_writer.load()
        index_writer.add_url(tflow.tflow())
        index_writer.save()


class TestSetEncoder:

    def test_set_encoder_set(self):
        test_set = {"foo", "bar", "42"}
        result = SetEncoder.default(SetEncoder(), test_set)
        assert isinstance(result, List)
        assert 'foo' in result
        assert 'bar' in result
        assert '42' in result

    def test_set_encoder_str(self):
        test_str = "test"
        try:
            SetEncoder.default(SetEncoder(), test_str)
        except TypeError:
            assert True
        else:
            assert False


class TestJSONUrlIndexWriter:

    def test_load(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write(
                "{\"http://example.com:80\": {\"/\": {\"GET\": [301]}}, \"http://www.example.com:80\": {\"/\": {\"GET\": [302]}}}")
        writer = JSONUrlIndexWriter(filename=tmpfile)
        writer.load()
        assert 'http://example.com:80' in writer.host_urls
        assert '/' in writer.host_urls['http://example.com:80']
        assert 'GET' in writer.host_urls['http://example.com:80']['/']
        assert 301 in writer.host_urls['http://example.com:80']['/']['GET']

    def test_load_empty(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write("{}")
        writer = JSONUrlIndexWriter(filename=tmpfile)
        writer.load()
        assert len(writer.host_urls) == 0

    def test_load_nonexisting(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        writer = JSONUrlIndexWriter(filename=tmpfile)
        writer.load()
        assert len(writer.host_urls) == 0

    def test_add(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        writer = JSONUrlIndexWriter(filename=tmpfile)
        f = tflow.tflow(resp=tutils.tresp())
        url = f"{f.request.scheme}://{f.request.host}:{f.request.port}"
        writer.add_url(f)
        assert url in writer.host_urls
        assert f.request.path in writer.host_urls[url]

    def test_save(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        writer = JSONUrlIndexWriter(filename=tmpfile)
        f = tflow.tflow(resp=tutils.tresp())
        url = f"{f.request.scheme}://{f.request.host}:{f.request.port}"
        writer.add_url(f)
        writer.save()

        with open(tmpfile) as results:
            try:
                content = json.load(results)
            except JSONDecodeError:
                assert False
            assert url in content


class TestTestUrlIndexWriter:
    def test_load(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write(
                "2020-04-22T05:41:08.679231 STATUS: 200 METHOD: GET URL:http://example.com")
        writer = TextUrlIndexWriter(filename=tmpfile)
        writer.load()
        assert True

    def test_load_empty(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write("{}")
        writer = TextUrlIndexWriter(filename=tmpfile)
        writer.load()
        assert True

    def test_load_nonexisting(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        writer = TextUrlIndexWriter(filename=tmpfile)
        writer.load()
        assert True

    def test_add(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        writer = TextUrlIndexWriter(filename=tmpfile)
        f = tflow.tflow(resp=tutils.tresp())
        url = f"{f.request.scheme}://{f.request.host}:{f.request.port}"
        method = f.request.method
        code = f.response.status_code
        writer.add_url(f)

        with open(tmpfile) as results:
            content = results.read()
        assert url in content
        assert method in content
        assert str(code) in content

    def test_save(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        writer = TextUrlIndexWriter(filename=tmpfile)
        f = tflow.tflow(resp=tutils.tresp())
        url = f"{f.request.scheme}://{f.request.host}:{f.request.port}"
        method = f.request.method
        code = f.response.status_code
        writer.add_url(f)
        writer.save()

        with open(tmpfile) as results:
            content = results.read()
        assert url in content
        assert method in content
        assert str(code) in content


class TestWriter:
    def test_writer_dict(self):
        assert "json" in WRITER
        assert isinstance(WRITER["json"], JSONUrlIndexWriter.__class__)
        assert "text" in WRITER
        assert isinstance(WRITER["text"], TextUrlIndexWriter.__class__)


class TestFilter:
    def test_filer_true(self):
        f = tflow.tflow(resp=tutils.tresp())
        assert filter_404(f)

    def test_filter_false(self):
        f = tflow.tflow(resp=tutils.tresp())
        f.response.status_code = 404
        assert not filter_404(f)


class TestUrlIndexAddon:

    def test_init(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        UrlIndexAddon(tmpfile)

    def test_init_format(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        try:
            UrlIndexAddon(tmpfile, index_format="test")
        except ValueError:
            assert True
        else:
            assert False

    def test_init_filter(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        try:
            UrlIndexAddon(tmpfile, index_filter="i~nvalid")
        except ValueError:
            assert True
        else:
            assert False

    def test_init_append(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write("")
        url_index = UrlIndexAddon(tmpfile, append=False)
        f = tflow.tflow(resp=tutils.tresp())
        with mock.patch('examples.complex.webscanner_helper.urlindex.JSONUrlIndexWriter.add_url'):
            url_index.response(f)
        assert not Path(tmpfile).exists()

    def test_response(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        url_index = UrlIndexAddon(tmpfile)
        f = tflow.tflow(resp=tutils.tresp())
        with mock.patch('examples.complex.webscanner_helper.urlindex.JSONUrlIndexWriter.add_url') as mock_add_url:
            url_index.response(f)
        mock_add_url.assert_called()

    def test_response_None(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        url_index = UrlIndexAddon(tmpfile)
        url_index.index_filter = None
        f = tflow.tflow(resp=tutils.tresp())
        try:
            url_index.response(f)
        except ValueError:
            assert True
        else:
            assert False

    def test_done(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        url_index = UrlIndexAddon(tmpfile)
        with mock.patch('examples.complex.webscanner_helper.urlindex.JSONUrlIndexWriter.save') as mock_save:
            url_index.done()
        mock_save.assert_called()
