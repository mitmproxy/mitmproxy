import io
import contextlib
from unittest import mock

import pytest

from mitmproxy.utils import arg_check


@pytest.mark.parametrize('arg, output', [
    (["-T"], "-T is deprecated, please use --mode transparent instead"),
    (["-U"], "-U is deprecated, please use --mode upstream:SPEC instead"),
    (["--confdir"], "--confdir is deprecated.\n"
                    "Please use `--set confdir=value` instead.\n"
                    "To show all options and their default values use --options"),
    (["--palette"], "--palette is deprecated.\n"
                    "Please use `--set console_palette=value` instead.\n"
                    "To show all options and their default values use --options"),
    (["--wfile"], "--wfile is deprecated.\n"
                  "Please use `--save-stream-file` instead."),
    (["--eventlog"], "--eventlog has been removed."),
    (["--nonanonymous"], '--nonanonymous is deprecated.\n'
                         'Please use `--proxyauth SPEC` instead.\n'
                         'SPEC Format: "username:pass", "any" to accept any user/pass combination,\n'
                         '"@path" to use an Apache htpasswd file, or\n'
                         '"ldap[s]:url_server_ldap:dn_auth:password:dn_subtree" '
                         'for LDAP authentication.'),
    (["--replacements"], "--replacements is deprecated.\n"
                         "Please use `--modify-body` or `--modify-headers` instead."),
    (["--underscore_option"], "--underscore_option uses underscores, please use hyphens --underscore-option")
])
def test_check_args(arg, output):
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        with mock.patch('sys.argv') as m:
            m.__getitem__.return_value = arg
            arg_check.check()
            assert f.getvalue().strip() == output
