import json
import base64

from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons

import requests_mock

example_dir = tutils.test_data.push("../examples")


class TestJSONDump:
    def echo_response(self, request, context):
        self.request = {'json': request.json(), 'headers': request.headers}
        return ''

    def flow(self, resp_content=b'message'):
        times = dict(
            timestamp_start=746203272,
            timestamp_end=746203272,
        )

        # Create a dummy flow for testing
        return tflow.tflow(
            req=tutils.treq(method=b'GET', **times),
            resp=tutils.tresp(content=resp_content, **times)
        )

    def test_simple(self, tmpdir):
        with taddons.context() as tctx:
            a = tctx.script(example_dir.path("complex/jsondump.py"))
            path = str(tmpdir.join("jsondump.out"))
            tctx.configure(a, dump_destination=path)
            tctx.invoke(a, "response", self.flow())
            tctx.invoke(a, "done")
            with open(path) as inp:
                entry = json.loads(inp.readline())
            assert entry['response']['content'] == 'message'

    def test_contentencode(self, tmpdir):
        with taddons.context() as tctx:
            a = tctx.script(example_dir.path("complex/jsondump.py"))
            path = str(tmpdir.join("jsondump.out"))
            content = b"foo" + b"\xFF" * 10
            tctx.configure(a, dump_destination=path, dump_encodecontent=True)

            tctx.invoke(
                a, "response", self.flow(resp_content=content)
            )
            tctx.invoke(a, "done")
            with open(path) as inp:
                entry = json.loads(inp.readline())
            assert entry['response']['content'] == base64.b64encode(content).decode('utf-8')

    def test_http(self, tmpdir):
        with requests_mock.Mocker() as mock:
            mock.post('http://my-server', text=self.echo_response)
            with taddons.context() as tctx:
                a = tctx.script(example_dir.path("complex/jsondump.py"))
                tctx.configure(a, dump_destination='http://my-server',
                               dump_username='user', dump_password='pass')

                tctx.invoke(a, "response", self.flow())
                tctx.invoke(a, "done")

                assert self.request['json']['response']['content'] == 'message'
                assert self.request['headers']['Authorization'] == 'Basic dXNlcjpwYXNz'
