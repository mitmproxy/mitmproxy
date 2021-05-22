import pytest
import requests
from examples.complex import xss_scanner as xss
from mitmproxy.test import tflow, tutils


class TestXSSScanner():
    def test_get_XSS_info(self):
        # First type of exploit: <script>PAYLOAD</script>
        # Exploitable:
        xss_info = xss.get_XSS_data(b"<html><script>%s</script><html>" %
                                    xss.FULL_PAYLOAD,
                                    "https://example.com",
                                    "End of URL")
        expected_xss_info = xss.XSSData('https://example.com',
                                        "End of URL",
                                        '</script><script>alert(0)</script><script>',
                                        xss.FULL_PAYLOAD.decode('utf-8'))
        assert xss_info == expected_xss_info
        xss_info = xss.get_XSS_data(b"<html><script>%s</script><html>" %
                                    xss.FULL_PAYLOAD.replace(b"'", b"%27").replace(b'"', b"%22"),
                                    "https://example.com",
                                    "End of URL")
        expected_xss_info = xss.XSSData("https://example.com",
                                        "End of URL",
                                        '</script><script>alert(0)</script><script>',
                                        xss.FULL_PAYLOAD.replace(b"'", b"%27").replace(b'"', b"%22").decode('utf-8'))
        assert xss_info == expected_xss_info
        # Non-Exploitable:
        xss_info = xss.get_XSS_data(b"<html><script>%s</script><html>" %
                                    xss.FULL_PAYLOAD.replace(b"'", b"%27").replace(b'"', b"%22").replace(b"/", b"%2F"),
                                    "https://example.com",
                                    "End of URL")
        assert xss_info is None
        # Second type of exploit: <script>t='PAYLOAD'</script>
        # Exploitable:
        xss_info = xss.get_XSS_data(b"<html><script>t='%s';</script></html>" %
                                    xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E").replace(b"\"", b"%22"),
                                    "https://example.com",
                                    "End of URL")
        expected_xss_info = xss.XSSData("https://example.com",
                                        "End of URL",
                                        "';alert(0);g='",
                                        xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E")
                                        .replace(b"\"", b"%22").decode('utf-8'))
        assert xss_info == expected_xss_info
        # Non-Exploitable:
        xss_info = xss.get_XSS_data(b"<html><script>t='%s';</script></html>" %
                                    xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b"\"", b"%22").replace(b"'", b"%22"),
                                    "https://example.com",
                                    "End of URL")
        assert xss_info is None
        # Third type of exploit: <script>t="PAYLOAD"</script>
        # Exploitable:
        xss_info = xss.get_XSS_data(b"<html><script>t=\"%s\";</script></html>" %
                                    xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E").replace(b"'", b"%27"),
                                    "https://example.com",
                                    "End of URL")
        expected_xss_info = xss.XSSData("https://example.com",
                                        "End of URL",
                                        '";alert(0);g="',
                                        xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E")
                                        .replace(b"'", b"%27").decode('utf-8'))
        assert xss_info == expected_xss_info
        # Non-Exploitable:
        xss_info = xss.get_XSS_data(b"<html><script>t=\"%s\";</script></html>" %
                                    xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b"'", b"%27").replace(b"\"", b"%22"),
                                    "https://example.com",
                                    "End of URL")
        assert xss_info is None
        # Fourth type of exploit: <a href='PAYLOAD'>Test</a>
        # Exploitable:
        xss_info = xss.get_XSS_data(b"<html><a href='%s'>Test</a></html>" %
                                    xss.FULL_PAYLOAD,
                                    "https://example.com",
                                    "End of URL")
        expected_xss_info = xss.XSSData("https://example.com",
                                        "End of URL",
                                        "'><script>alert(0)</script>",
                                        xss.FULL_PAYLOAD.decode('utf-8'))
        assert xss_info == expected_xss_info
        # Non-Exploitable:
        xss_info = xss.get_XSS_data(b"<html><a href='OtherStuff%s'>Test</a></html>" %
                                    xss.FULL_PAYLOAD.replace(b"'", b"%27"),
                                    "https://example.com",
                                    "End of URL")
        assert xss_info is None
        # Fifth type of exploit: <a href="PAYLOAD">Test</a>
        # Exploitable:
        xss_info = xss.get_XSS_data(b"<html><a href=\"%s\">Test</a></html>" %
                                    xss.FULL_PAYLOAD.replace(b"'", b"%27"),
                                    "https://example.com",
                                    "End of URL")
        expected_xss_info = xss.XSSData("https://example.com",
                                        "End of URL",
                                        "\"><script>alert(0)</script>",
                                        xss.FULL_PAYLOAD.replace(b"'", b"%27").decode('utf-8'))
        assert xss_info == expected_xss_info
        # Non-Exploitable:
        xss_info = xss.get_XSS_data(b"<html><a href=\"OtherStuff%s\">Test</a></html>" %
                                    xss.FULL_PAYLOAD.replace(b"'", b"%27").replace(b"\"", b"%22"),
                                    "https://example.com",
                                    "End of URL")
        assert xss_info is None
        # Sixth type of exploit: <a href=PAYLOAD>Test</a>
        # Exploitable:
        xss_info = xss.get_XSS_data(b"<html><a href=%s>Test</a></html>" %
                                    xss.FULL_PAYLOAD,
                                    "https://example.com",
                                    "End of URL")
        expected_xss_info = xss.XSSData("https://example.com",
                                        "End of URL",
                                        "><script>alert(0)</script>",
                                        xss.FULL_PAYLOAD.decode('utf-8'))
        assert xss_info == expected_xss_info
        # Non-Exploitable
        xss_info = xss.get_XSS_data(b"<html><a href=OtherStuff%s>Test</a></html>" %
                                    xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E")
                                    .replace(b"=", b"%3D"),
                                    "https://example.com",
                                    "End of URL")
        assert xss_info is None
        # Seventh type of exploit: <html>PAYLOAD</html>
        # Exploitable:
        xss_info = xss.get_XSS_data(b"<html><b>%s</b></html>" %
                                    xss.FULL_PAYLOAD,
                                    "https://example.com",
                                    "End of URL")
        expected_xss_info = xss.XSSData("https://example.com",
                                        "End of URL",
                                        "<script>alert(0)</script>",
                                        xss.FULL_PAYLOAD.decode('utf-8'))
        assert xss_info == expected_xss_info
        # Non-Exploitable
        xss_info = xss.get_XSS_data(b"<html><b>%s</b></html>" %
                                    xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E").replace(b"/", b"%2F"),
                                    "https://example.com",
                                    "End of URL")
        assert xss_info is None
        # Eighth type of exploit: <a href=PAYLOAD>Test</a>
        # Exploitable:
        xss_info = xss.get_XSS_data(b"<html><a href=%s>Test</a></html>" %
                                    xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E"),
                                    "https://example.com",
                                    "End of URL")
        expected_xss_info = xss.XSSData("https://example.com",
                                        "End of URL",
                                        "Javascript:alert(0)",
                                        xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E").decode('utf-8'))
        assert xss_info == expected_xss_info
        # Non-Exploitable:
        xss_info = xss.get_XSS_data(b"<html><a href=OtherStuff%s>Test</a></html>" %
                                    xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E")
                                    .replace(b"=", b"%3D"),
                                    "https://example.com",
                                    "End of URL")
        assert xss_info is None
        # Ninth type of exploit: <a href="STUFF PAYLOAD">Test</a>
        # Exploitable:
        xss_info = xss.get_XSS_data(b"<html><a href=\"STUFF %s\">Test</a></html>" %
                                    xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E"),
                                    "https://example.com",
                                    "End of URL")
        expected_xss_info = xss.XSSData("https://example.com",
                                        "End of URL",
                                        '" onmouseover="alert(0)" t="',
                                        xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E").decode('utf-8'))
        assert xss_info == expected_xss_info
        # Non-Exploitable:
        xss_info = xss.get_XSS_data(b"<html><a href=\"STUFF %s\">Test</a></html>" %
                                    xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E")
                                    .replace(b'"', b"%22"),
                                    "https://example.com",
                                    "End of URL")
        assert xss_info is None
        # Tenth type of exploit: <a href='STUFF PAYLOAD'>Test</a>
        # Exploitable:
        xss_info = xss.get_XSS_data(b"<html><a href='STUFF %s'>Test</a></html>" %
                                    xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E"),
                                    "https://example.com",
                                    "End of URL")
        expected_xss_info = xss.XSSData("https://example.com",
                                        "End of URL",
                                        "' onmouseover='alert(0)' t='",
                                        xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E").decode('utf-8'))
        assert xss_info == expected_xss_info
        # Non-Exploitable:
        xss_info = xss.get_XSS_data(b"<html><a href='STUFF %s'>Test</a></html>" %
                                    xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E")
                                    .replace(b"'", b"%22"),
                                    "https://example.com",
                                    "End of URL")
        assert xss_info is None
        # Eleventh type of exploit: <a href=STUFF_PAYLOAD>Test</a>
        # Exploitable:
        xss_info = xss.get_XSS_data(b"<html><a href=STUFF%s>Test</a></html>" %
                                    xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E"),
                                    "https://example.com",
                                    "End of URL")
        expected_xss_info = xss.XSSData("https://example.com",
                                        "End of URL",
                                        " onmouseover=alert(0) t=",
                                        xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E").decode('utf-8'))
        assert xss_info == expected_xss_info
        # Non-Exploitable:
        xss_info = xss.get_XSS_data(b"<html><a href=STUFF_%s>Test</a></html>" %
                                    xss.FULL_PAYLOAD.replace(b"<", b"%3C").replace(b">", b"%3E")
                                    .replace(b"=", b"%3D"),
                                    "https://example.com",
                                    "End of URL")
        assert xss_info is None

    def test_get_SQLi_data(self):
        sqli_data = xss.get_SQLi_data("<html>SQL syntax MySQL</html>",
                                      "<html></html>",
                                      "https://example.com",
                                      "End of URL")
        expected_sqli_data = xss.SQLiData("https://example.com",
                                          "End of URL",
                                          "SQL syntax.*MySQL",
                                          "MySQL")
        assert sqli_data == expected_sqli_data
        sqli_data = xss.get_SQLi_data("<html>SQL syntax MySQL</html>",
                                      "<html>SQL syntax MySQL</html>",
                                      "https://example.com",
                                      "End of URL")
        assert sqli_data is None

    def test_inside_quote(self):
        assert not xss.inside_quote("'", b"no", 0, b"no")
        assert xss.inside_quote("'", b"yes", 0, b"'yes'")
        assert xss.inside_quote("'", b"yes", 1, b"'yes'otherJunk'yes'more")
        assert not xss.inside_quote("'", b"longStringNotInIt", 1, b"short")

    def test_paths_to_text(self):
        text = xss.paths_to_text("""<html><head><h1>STRING</h1></head>
                                    <script>STRING</script>
                                    <a href=STRING></a></html>""", "STRING")
        expected_text = ["/html/head/h1", "/html/script"]
        assert text == expected_text
        assert xss.paths_to_text("""<html></html>""", "STRING") == []

    def mocked_requests_vuln(*args, headers=None, cookies=None):
        class MockResponse:
            def __init__(self, html, headers=None, cookies=None):
                self.text = html
        return MockResponse("<html>%s</html>" % xss.FULL_PAYLOAD)

    def mocked_requests_invuln(*args, headers=None, cookies=None):
        class MockResponse:
            def __init__(self, html, headers=None, cookies=None):
                self.text = html
        return MockResponse("<html></html>")

    def test_test_end_of_url_injection(self, get_request_vuln):
        xss_info = xss.test_end_of_URL_injection("<html></html>", "https://example.com/index.html", {})[0]
        expected_xss_info = xss.XSSData('https://example.com/index.html/1029zxcs\'d"ao<ac>so[sb]po(pc)se;sl/bsl\\eq=3847asd',
                                        'End of URL',
                                        '<script>alert(0)</script>',
                                        '1029zxcs\\\'d"ao<ac>so[sb]po(pc)se;sl/bsl\\\\eq=3847asd')
        sqli_info = xss.test_end_of_URL_injection("<html></html>", "https://example.com/", {})[1]
        assert xss_info == expected_xss_info
        assert sqli_info is None

    def test_test_referer_injection(self, get_request_vuln):
        xss_info = xss.test_referer_injection("<html></html>", "https://example.com/", {})[0]
        expected_xss_info = xss.XSSData('https://example.com/',
                                        'Referer',
                                        '<script>alert(0)</script>',
                                        '1029zxcs\\\'d"ao<ac>so[sb]po(pc)se;sl/bsl\\\\eq=3847asd')
        sqli_info = xss.test_referer_injection("<html></html>", "https://example.com/", {})[1]
        assert xss_info == expected_xss_info
        assert sqli_info is None

    def test_test_user_agent_injection(self, get_request_vuln):
        xss_info = xss.test_user_agent_injection("<html></html>", "https://example.com/", {})[0]
        expected_xss_info = xss.XSSData('https://example.com/',
                                        'User Agent',
                                        '<script>alert(0)</script>',
                                        '1029zxcs\\\'d"ao<ac>so[sb]po(pc)se;sl/bsl\\\\eq=3847asd')
        sqli_info = xss.test_user_agent_injection("<html></html>", "https://example.com/", {})[1]
        assert xss_info == expected_xss_info
        assert sqli_info is None

    def test_test_query_injection(self, get_request_vuln):

        xss_info = xss.test_query_injection("<html></html>", "https://example.com/vuln.php?cmd=ls", {})[0]
        expected_xss_info = xss.XSSData('https://example.com/vuln.php?cmd=1029zxcs\'d"ao<ac>so[sb]po(pc)se;sl/bsl\\eq=3847asd',
                                        'Query',
                                        '<script>alert(0)</script>',
                                        '1029zxcs\\\'d"ao<ac>so[sb]po(pc)se;sl/bsl\\\\eq=3847asd')
        sqli_info = xss.test_query_injection("<html></html>", "https://example.com/vuln.php?cmd=ls", {})[1]
        assert xss_info == expected_xss_info
        assert sqli_info is None

    @pytest.fixture(scope='function')
    def logger(self, monkeypatch):
        class Logger():
            def __init__(self):
                self.args = []

            def info(self, str):
                self.args.append(str)

            def error(self, str):
                self.args.append(str)

        logger = Logger()
        monkeypatch.setattr("mitmproxy.ctx.log", logger)
        yield logger

    @pytest.fixture(scope='function')
    def get_request_vuln(self, monkeypatch):
        monkeypatch.setattr(requests, 'get', self.mocked_requests_vuln)

    @pytest.fixture(scope='function')
    def get_request_invuln(self, monkeypatch):
        monkeypatch.setattr(requests, 'get', self.mocked_requests_invuln)

    @pytest.fixture(scope='function')
    def mock_gethostbyname(self, monkeypatch):
        def gethostbyname(domain):
            claimed_domains = ["google.com"]
            if domain not in claimed_domains:
                from socket import gaierror
                raise gaierror("[Errno -2] Name or service not known")
            else:
                return '216.58.221.46'

        monkeypatch.setattr("socket.gethostbyname", gethostbyname)

    def test_find_unclaimed_URLs(self, logger, mock_gethostbyname):
        xss.find_unclaimed_URLs("<html><script src=\"http://google.com\"></script></html>",
                                "https://example.com")
        assert logger.args == []
        xss.find_unclaimed_URLs("<html><script src=\"http://unclaimedDomainName.com\"></script></html>",
                                "https://example.com")
        assert logger.args[0] == 'XSS found in https://example.com due to unclaimed URL "http://unclaimedDomainName.com".'
        xss.find_unclaimed_URLs("<html><iframe src=\"http://unclaimedDomainName.com\"></iframe></html>",
                                "https://example.com")
        assert logger.args[1] == 'XSS found in https://example.com due to unclaimed URL "http://unclaimedDomainName.com".'
        xss.find_unclaimed_URLs("<html><link rel=\"stylesheet\" href=\"http://unclaimedDomainName.com\"></html>",
                                "https://example.com")
        assert logger.args[2] == 'XSS found in https://example.com due to unclaimed URL "http://unclaimedDomainName.com".'

    def test_log_XSS_data(self, logger):
        xss.log_XSS_data(None)
        assert logger.args == []
        # self, url: str, injection_point: str, exploit: str, line: str
        xss.log_XSS_data(xss.XSSData('https://example.com',
                                     'Location',
                                     'String',
                                     'Line of HTML'))
        assert logger.args[0] == '===== XSS Found ===='
        assert logger.args[1] == 'XSS URL: https://example.com'
        assert logger.args[2] == 'Injection Point: Location'
        assert logger.args[3] == 'Suggested Exploit: String'
        assert logger.args[4] == 'Line: Line of HTML'

    def test_log_SQLi_data(self, logger):
        xss.log_SQLi_data(None)
        assert logger.args == []
        xss.log_SQLi_data(xss.SQLiData('https://example.com',
                                       'Location',
                                       'Oracle.*Driver',
                                       'Oracle'))
        assert logger.args[0] == '===== SQLi Found ====='
        assert logger.args[1] == 'SQLi URL: https://example.com'
        assert logger.args[2] == 'Injection Point: Location'
        assert logger.args[3] == 'Regex used: Oracle.*Driver'

    def test_get_cookies(self):
        mocked_req = tutils.treq()
        mocked_req.cookies = [("cookieName2", "cookieValue2")]
        mocked_flow = tflow.tflow(req=mocked_req)
        # It only uses the request cookies
        assert xss.get_cookies(mocked_flow) == {"cookieName2": "cookieValue2"}

    def test_response(self, get_request_invuln, logger):
        mocked_flow = tflow.tflow(
            req=tutils.treq(path=b"index.html?q=1"),
            resp=tutils.tresp(content=b'<html></html>')
        )
        xss.response(mocked_flow)
        assert logger.args == []

    def test_data_equals(self):
        xssData = xss.XSSData("a", "b", "c", "d")
        sqliData = xss.SQLiData("a", "b", "c", "d")
        assert xssData == xssData
        assert sqliData == sqliData
