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
            mock_http.return_value.getresponse.return_value = mock.MagicMock(status=204, reason="No Content")
            sh.share([tflow.tflow(resp=True)])
            assert tctx.master.has_log("https://share.mitmproxy.org/")

            mock_http.return_value.getresponse.return_value = mock.MagicMock(status=403, reason="Forbidden")
            sh.share([tflow.tflow(resp=True)])
            assert tctx.master.has_log("Forbidden")

            mock_http.return_value.getresponse.return_value = mock.MagicMock(status=404, reason="")
            sh.share([tflow.tflow(resp=True)])
            assert tctx.master.has_log("Not Found")

            mock_http.return_value.request.side_effect = http.client.CannotSendRequest("Error in sending req")
            sh.share([tflow.tflow(resp=True)])
            assert tctx.master.has_log("Error in sending req")

            v = view.View()
            tctx.master.addons.add(v)
            tctx.master.addons.add(sh)
            tctx.master.commands.call_args("share.flows", ["@shown"])
