from unittest import mock
from unittest.mock import MagicMock

import pytest

from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.http import HTTPFlow

from examples.contrib.webscanner_helper.proxyauth_selenium import logger, randomString, AuthorizationOracle, \
    SeleniumAddon


class TestRandomString:

    def test_random_string(self):
        res = randomString()
        assert isinstance(res, str)
        assert len(res) == 10

        res_5 = randomString(5)
        assert isinstance(res_5, str)
        assert len(res_5) == 5


class AuthenticationOracleTest(AuthorizationOracle):
    def is_unauthorized_request(self, flow: HTTPFlow) -> bool:
        return True

    def is_unauthorized_response(self, flow: HTTPFlow) -> bool:
        return True


oracle = AuthenticationOracleTest()


@pytest.fixture(scope="module", autouse=True)
def selenium_addon(request):
    addon = SeleniumAddon(fltr=r"~u http://example\.com/login\.php", domain=r"~d http://example\.com",
                          auth_oracle=oracle)
    browser = MagicMock()
    addon.browser = browser
    yield addon

    def fin():
        addon.browser.close()

    request.addfinalizer(fin)


class TestSeleniumAddon:

    def test_request_replay(self, selenium_addon):
        f = tflow.tflow(resp=tutils.tresp())
        f.request.is_replay = True
        with mock.patch.object(logger, 'warning') as mock_warning:
            selenium_addon.request(f)
        mock_warning.assert_called()

    def test_request(self, selenium_addon):
        f = tflow.tflow(resp=tutils.tresp())
        f.request.url = "http://example.com/login.php"
        selenium_addon.set_cookies = False
        assert not selenium_addon.set_cookies
        with mock.patch.object(logger, 'debug') as mock_debug:
            selenium_addon.request(f)
        mock_debug.assert_called()
        assert selenium_addon.set_cookies

    def test_request_filtered(self, selenium_addon):
        f = tflow.tflow(resp=tutils.tresp())
        selenium_addon.set_cookies = False
        assert not selenium_addon.set_cookies
        selenium_addon.request(f)
        assert not selenium_addon.set_cookies

    def test_request_cookies(self, selenium_addon):
        f = tflow.tflow(resp=tutils.tresp())
        f.request.url = "http://example.com/login.php"
        selenium_addon.set_cookies = False
        assert not selenium_addon.set_cookies
        with mock.patch.object(logger, 'debug') as mock_debug:
            with mock.patch('examples.complex.webscanner_helper.proxyauth_selenium.SeleniumAddon.login',
                            return_value=[{"name": "cookie", "value": "test"}]) as mock_login:
                selenium_addon.request(f)
        mock_debug.assert_called()
        assert selenium_addon.set_cookies
        mock_login.assert_called()

    def test_request_filter_None(self, selenium_addon):
        f = tflow.tflow(resp=tutils.tresp())
        fltr = selenium_addon.filter
        selenium_addon.filter = None
        assert not selenium_addon.filter
        selenium_addon.set_cookies = False
        assert not selenium_addon.set_cookies

        with mock.patch.object(logger, 'debug') as mock_debug:
            selenium_addon.request(f)
        mock_debug.assert_called()
        selenium_addon.filter = fltr
        assert selenium_addon.set_cookies

    def test_response(self, selenium_addon):
        f = tflow.tflow(resp=tutils.tresp())
        f.request.url = "http://example.com/login.php"
        selenium_addon.set_cookies = False
        with mock.patch('examples.complex.webscanner_helper.proxyauth_selenium.SeleniumAddon.login',
                        return_value=[]) as mock_login:
            selenium_addon.response(f)
        mock_login.assert_called()

    def test_response_cookies(self, selenium_addon):
        f = tflow.tflow(resp=tutils.tresp())
        f.request.url = "http://example.com/login.php"
        selenium_addon.set_cookies = False
        with mock.patch('examples.complex.webscanner_helper.proxyauth_selenium.SeleniumAddon.login',
                        return_value=[{"name": "cookie", "value": "test"}]) as mock_login:
            selenium_addon.response(f)
        mock_login.assert_called()
