import mock
import socket
import os
import time
from libmproxy import dump
from netlib import certutils, tcp
from libpathod.pathoc import Pathoc
import tutils
import tservers


class TestApp(tservers.HTTPProxTest):
    def test_basic(self):
        assert self.app("/").status_code == 200

    def test_cert(self):
        with tutils.tmpdir() as d:
            for ext in ["pem", "p12"]:
                resp = self.app("/cert/%s" % ext)
                assert resp.status_code == 200
                assert resp.content
