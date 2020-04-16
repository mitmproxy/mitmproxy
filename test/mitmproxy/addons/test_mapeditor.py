import tempfile
import os
import pytest

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
            # test matching rules
            text_test_fp = os.path.join(tempfile.gettempdir(), os.urandom(24).hex())
            with open(text_test_fp, "w") as f:
                f.write("TEST FOR MAPEDITOR PAGE: replaced by mapeditor")
            tctx.configure(
                me,
                mapeditor = [
                    "~u .*://example.com/script.js:MAP_TO:" + text_test_fp
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
            os.remove(text_test_fp)

            # test for binary text
            binary_test_fp = os.path.join(tempfile.gettempdir(), os.urandom(24).hex())
            with open(binary_test_fp, "wb") as f:
                f.write(b"TEST FOR MAPEDITOR PAGE: binary\x01\x02\xff")
            tctx.configure(
                me,
                mapeditor = [
                    "~u .*://example.com/script.js:MAP_TO:" + binary_test_fp
                ]
            )
            f = tflow.tflow(resp=True)
            f.request.url = "http://example.com/script.js"
            f.response.content = b"TEST FOR MAPEDITOR PAGE: not replaced"
            me.response(f)
            assert f.response.raw_content == b"TEST FOR MAPEDITOR PAGE: binary\x01\x02\xff"
            os.remove(binary_test_fp)

            # test none exist file
            none_exist_tempf = tempfile.mktemp(prefix="mitmproxy_test")
            tctx.configure(
                me,
                mapeditor = [
                    "~u .*://example.com/script.js:MAP_TO:" + none_exist_tempf
                ]
            )
            f = tflow.tflow(resp=True)
            f.request.url = "http://example.com/script.js"
            f.response.text = "TEST FOR MAPEDITOR PAGE: not replaced"
            with pytest.raises(Exception, match="Failed to open file"):
                me.response(f)