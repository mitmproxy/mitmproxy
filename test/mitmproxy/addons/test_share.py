from unittest import mock
import http.client

from mitmproxy.test import taddons
from mitmproxy.test import tflow

from mitmproxy.addons import share
from mitmproxy.addons import view


def test_share_command():
    with mock.patch('mitmproxy.addons.share.http.client.HTTPConnection') as mock_http:
        sh = share.Share()
        with taddons.context() as tctx:
            sh.share([tflow.tflow(resp=True)])
            assert tctx.master.has_log("URL: share.mitmproxy.org/")

            mock_http.return_value.getresponse.side_effect = http.client.RemoteDisconnected
            sh.share([tflow.tflow(resp=True)])
            assert tctx.master.has_log("The server couldn\'t fulfill the request.")

            mock_http.return_value.request.side_effect = http.client.CannotSendRequest
            sh.share([tflow.tflow(resp=True)])
            assert tctx.master.has_log("We failed to reach a server.")

            v = view.View()
            tctx.master.addons.add(v)
            tctx.master.addons.add(sh)
            tctx.master.commands.call_args("share.flows", ["@shown"])
