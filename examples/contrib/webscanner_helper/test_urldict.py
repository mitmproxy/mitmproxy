from mitmproxy.test import tflow, tutils
from examples.contrib.webscanner_helper.urldict import URLDict

url = "http://10.10.10.10"
new_content_body = "New Body"
new_content_title = "New Title"
content = f'{{"body": "{new_content_body}", "title": "{new_content_title}"}}'
url_error = "i~nvalid"
input_file_content = f'{{"{url}": {content}}}'
input_file_content_error = f'{{"{url_error}": {content}}}'


class TestUrlDict:

    def test_urldict_empty(self):
        urldict = URLDict()
        dump = urldict.dumps()
        assert dump == '{}'

    def test_urldict_loads(self):
        urldict = URLDict.loads(input_file_content)
        dump = urldict.dumps()
        assert dump == input_file_content

    def test_urldict_set_error(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write(input_file_content_error)
        with open(tmpfile) as tfile:
            try:
                URLDict.load(tfile)
            except ValueError:
                assert True
            else:
                assert False

    def test_urldict_get(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write(input_file_content)
        with open(tmpfile) as tfile:
            urldict = URLDict.load(tfile)

        f = tflow.tflow(resp=tutils.tresp())
        f.request.url = url
        selection = urldict[f]
        assert "body" in selection[0]
        assert new_content_body in selection[0]["body"]
        assert "title" in selection[0]
        assert new_content_title in selection[0]["title"]

        selection_get = urldict.get(f)
        assert "body" in selection_get[0]
        assert new_content_body in selection_get[0]["body"]
        assert "title" in selection_get[0]
        assert new_content_title in selection_get[0]["title"]

        try:
            urldict["body"]
        except KeyError:
            assert True
        else:
            assert False

        assert urldict.get("body", default="default") == "default"

    def test_urldict_dumps(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            tfile.write(input_file_content)
        with open(tmpfile) as tfile:
            urldict = URLDict.load(tfile)

        dump = urldict.dumps()
        assert dump == input_file_content

    def test_urldict_dump(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        outfile = tmpdir.join("outfile")
        with open(tmpfile, "w") as tfile:
            tfile.write(input_file_content)
        with open(tmpfile) as tfile:
            urldict = URLDict.load(tfile)
        with open(outfile, "w") as ofile:
            urldict.dump(ofile)

        with open(outfile) as ofile:
            output = ofile.read()
        assert output == input_file_content
