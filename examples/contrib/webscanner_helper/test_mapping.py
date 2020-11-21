from typing import TextIO, Callable
from unittest import mock
from unittest.mock import MagicMock

from mitmproxy.test import tflow
from mitmproxy.test import tutils

from examples.contrib.webscanner_helper.mapping import MappingAddon, MappingAddonConfig


class TestConfig:

    def test_config(self):
        assert MappingAddonConfig.HTML_PARSER == "html.parser"


url = "http://10.10.10.10"
new_content = "My Text"
mapping_content = f'{{"{url}": {{"body": "{new_content}"}}}}'


class TestMappingAddon:

    def test_init(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write(mapping_content)
        mapping = MappingAddon(tmpfile)
        assert "My Text" in str(mapping.mapping_templates._dump())

    def test_load(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write(mapping_content)
        mapping = MappingAddon(tmpfile)
        loader = MagicMock()

        mapping.load(loader)
        assert 'mapping_file' in str(loader.add_option.call_args_list)
        assert 'map_persistent' in str(loader.add_option.call_args_list)

    def test_configure(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write(mapping_content)
        mapping = MappingAddon(tmpfile)
        new_filename = "My new filename"
        updated = {str(mapping.OPT_MAPPING_FILE): new_filename, str(mapping.OPT_MAP_PERSISTENT): True}

        open_mock = mock.mock_open(read_data="{}")
        with mock.patch("builtins.open", open_mock):
            mapping.configure(updated)
        assert new_filename in str(open_mock.mock_calls)
        assert mapping.filename == new_filename
        assert mapping.persistent

    def test_response_filtered(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write(mapping_content)
        mapping = MappingAddon(tmpfile)
        f = tflow.tflow(resp=tutils.tresp())
        test_content = b"Test"
        f.response.content = test_content

        mapping.response(f)
        assert f.response.content == test_content

    def test_response(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write(mapping_content)
        mapping = MappingAddon(tmpfile)
        f = tflow.tflow(resp=tutils.tresp())
        test_content = b"<body> Test </body>"
        f.response.content = test_content
        f.request.url = url

        mapping.response(f)
        assert f.response.content.decode("utf-8") == new_content

    def test_response_content_type(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write(mapping_content)
        mapping = MappingAddon(tmpfile)
        f = tflow.tflow(resp=tutils.tresp())
        test_content = b"<body> Test </body>"
        f.response.content = test_content
        f.request.url = url
        f.response.headers.add("content-type", "content-type")

        mapping.response(f)
        assert f.response.content == test_content

    def test_response_not_existing(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write(mapping_content)
        mapping = MappingAddon(tmpfile)
        f = tflow.tflow(resp=tutils.tresp())
        test_content = b"<title> Test </title>"
        f.response.content = test_content
        f.request.url = url
        mapping.response(f)
        assert f.response.content == test_content

    def test_persistance_false(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write(mapping_content)
        mapping = MappingAddon(tmpfile)

        open_mock = mock.mock_open(read_data="{}")
        with mock.patch("builtins.open", open_mock):
            mapping.done()
        assert len(open_mock.mock_calls) == 0

    def test_persistance_true(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write(mapping_content)
        mapping = MappingAddon(tmpfile, persistent=True)

        open_mock = mock.mock_open(read_data="{}")
        with mock.patch("builtins.open", open_mock):
            mapping.done()
        with open(tmpfile) as tfile:
            results = tfile.read()
        assert len(open_mock.mock_calls) != 0
        assert results == mapping_content

    def test_persistance_true_add_content(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write(mapping_content)
        mapping = MappingAddon(tmpfile, persistent=True)

        f = tflow.tflow(resp=tutils.tresp())
        test_content = b"<title> Test </title>"
        f.response.content = test_content
        f.request.url = url

        mapping.response(f)
        mapping.done()
        with open(tmpfile) as tfile:
            results = tfile.read()
        assert mapping_content in results

    def mock_dump(self, f: TextIO, value_dumper: Callable):
        assert value_dumper(None) == "None"
        try:
            value_dumper("Test")
        except RuntimeError:
            assert True
        else:
            assert False

    def test_dump(selfself, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write("{}")
        mapping = MappingAddon(tmpfile, persistent=True)
        with mock.patch('examples.complex.webscanner_helper.urldict.URLDict.dump', selfself.mock_dump):
            mapping.done()
