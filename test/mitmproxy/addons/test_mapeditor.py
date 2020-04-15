import os
import pytest
import platform

from mitmproxy.test import tflow
from mitmproxy.test import taddons

from mitmproxy.addons import mapeditor


class TestMapEditor:
    def test_parse_mapeditor(self):
        x = mapeditor.parse_mapeditor("~u .*://example.com/script.js:MAP_TO:/etc/hostname")
        assert x == ("~u .*://example.com/script.js", "/etc/hostname")
        with pytest.raises(Exception, match="Invalid map editor specifier"):
            mapeditor.parse_mapeditor("~u .*://example.com/script.js:FOO_TO:/etc/hostname")

    def test_configure(self):
        me = mapeditor.MapEditor()
        with taddons.context(me) as tctx:
            with pytest.raises(Exception, match="Invalid map editor filter pattern"):
                tctx.configure(me, mapeditor = ["~b:MAP_TO:/etc/hostname"])
            tctx.configure(me, mapeditor = ["foo:MAP_TO:/etc/hostname"])

    def test_mapeditor(self):
        me = mapeditor.MapEditor()
        with taddons.context(me) as tctx:
            if platform.system() == "Windows":
                none_exist_file_path = "C:\\windows\\temp\\none_exist_file"
                test_file_path = "C:\\windows\\temp\\mapeditor_test"
            else:
                none_exist_file_path = "/tmp/none_exist_file"
                test_file_path = "/tmp/mapeditor_test"

            with open(test_file_path, "w") as f:
                f.write("TEST FOR MAPEDITOR PAGE: replaced by mapeditor")
            tctx.configure(
                me,
                mapeditor = [
                    "~u .*://example.com/script.js:MAP_TO:" + test_file_path
                ]
            )

            # match the filter, response should be replaced
            f = tflow.tflow(resp=True)
            f.request.url = "http://example.com/script.js"
            f.response.text = "TEST FOR MAPEDITOR PAGE: not replaced"
            me.response(f)
            assert f.response.text == "TEST FOR MAPEDITOR PAGE: replaced by mapeditor"

            # did not match the filter, response text should not be replaced
            f = tflow.tflow(resp=True)
            f.request.url = "http://example.com/not_this_script.js"
            f.response.text = "TEST FOR MAPEDITOR PAGE: not replaced"
            me.response(f)
            assert f.response.text == "TEST FOR MAPEDITOR PAGE: not replaced"

            tctx.configure(
                me,
                mapeditor = [
                    "~u .*://example.com/script.js:MAP_TO:" + none_exist_file_path
                ]
            )
            # test none exist file
            f = tflow.tflow(resp=True)
            f.request.url = "http://example.com/script.js"
            f.response.text = "TEST FOR MAPEDITOR PAGE: not replaced"
            with pytest.raises(Exception, match="Failed to open file"):
                me.response(f)

            # clear tmp file
            os.remove(test_file_path)
