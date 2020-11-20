r"""

 __   __ _____ _____     _____
 \ \ / // ____/ ____|   / ____|
  \ V /| (___| (___    | (___   ___ __ _ _ __  _ __   ___ _ __
   > <  \___ \\___ \    \___ \ / __/ _` | '_ \| '_ \ / _ \ '__|
  / . \ ____) |___) |   ____) | (_| (_| | | | | | | |  __/ |
 /_/ \_\_____/_____/   |_____/ \___\__,_|_| |_|_| |_|\___|_|


This script automatically scans all visited webpages for XSS and SQLi vulnerabilities.

Usage: mitmproxy -s xss_scanner.py

This script scans for vulnerabilities by injecting a fuzzing payload (see PAYLOAD below) into 4 different places
and examining the HTML to look for XSS and SQLi injection vulnerabilities. The XSS scanning functionality works by
looking to see whether it is possible to inject HTML based off of of where the payload appears in the page and what
characters are escaped. In addition, it also looks for any script tags that load javascript from unclaimed domains.
The SQLi scanning functionality works by using regular expressions to look for errors from a number of different
common databases. Since it is only looking for errors, it will not find blind SQLi vulnerabilities.

The 4 places it injects the payload into are:
1. URLs         (e.g. https://example.com/ -> https://example.com/PAYLOAD/)
2. Queries      (e.g. https://example.com/index.html?a=b -> https://example.com/index.html?a=PAYLOAD)
3. Referers     (e.g. The referer changes from https://example.com to PAYLOAD)
4. User Agents  (e.g. The UA changes from Chrome to PAYLOAD)

Reports from this script show up in the event log (viewable by pressing e) and formatted like:

===== XSS Found ====
XSS URL: http://daviddworken.com/vulnerableUA.php
Injection Point: User Agent
Suggested Exploit: <script>alert(0)</script>
Line: 1029zxcs'd"ao<ac>so[sb]po(pc)se;sl/bsl\eq=3847asd

"""

from html.parser import HTMLParser
from typing import Dict, Union, Tuple, Optional, List, NamedTuple
from urllib.parse import urlparse
import re
import socket

import requests

from mitmproxy import http
from mitmproxy import ctx


# The actual payload is put between a frontWall and a backWall to make it easy
# to locate the payload with regular expressions
FRONT_WALL = b"1029zxc"
BACK_WALL = b"3847asd"
PAYLOAD = b"""s'd"ao<ac>so[sb]po(pc)se;sl/bsl\\eq="""
FULL_PAYLOAD = FRONT_WALL + PAYLOAD + BACK_WALL


# A XSSData is a named tuple with the following fields:
#   - url -> str
#   - injection_point -> str
#   - exploit -> str
#   - line -> str
class XSSData(NamedTuple):
    url: str
    injection_point: str
    exploit: str
    line: str


# A SQLiData is named tuple with the following fields:
#   - url -> str
#   - injection_point -> str
#   - regex -> str
#   - dbms -> str
class SQLiData(NamedTuple):
    url: str
    injection_point: str
    regex: str
    dbms: str


VulnData = Tuple[Optional[XSSData], Optional[SQLiData]]
Cookies = Dict[str, str]


def get_cookies(flow: http.HTTPFlow) -> Cookies:
    """ Return a dict going from cookie names to cookie values
          - Note that it includes both the cookies sent in the original request and
            the cookies sent by the server """
    return {name: value for name, value in flow.request.cookies.fields}


def find_unclaimed_URLs(body, requestUrl):
    """ Look for unclaimed URLs in script tags and log them if found"""
    def getValue(attrs: List[Tuple[str, str]], attrName: str) -> Optional[str]:
        for name, value in attrs:
            if attrName == name:
                return value
        return None

    class ScriptURLExtractor(HTMLParser):
        script_URLs: List[str] = []

        def handle_starttag(self, tag, attrs):
            if (tag == "script" or tag == "iframe") and "src" in [name for name, value in attrs]:
                self.script_URLs.append(getValue(attrs, "src"))
            if tag == "link" and getValue(attrs, "rel") == "stylesheet" and "href" in [name for name, value in attrs]:
                self.script_URLs.append(getValue(attrs, "href"))

    parser = ScriptURLExtractor()
    parser.feed(body)
    for url in parser.script_URLs:
        url_parser = urlparse(url)
        domain = url_parser.netloc
        try:
            socket.gethostbyname(domain)
        except socket.gaierror:
            ctx.log.error(f"XSS found in {requestUrl} due to unclaimed URL \"{url}\".")


def test_end_of_URL_injection(original_body: str, request_URL: str, cookies: Cookies) -> VulnData:
    """ Test the given URL for XSS via injection onto the end of the URL and
        log the XSS if found """
    parsed_URL = urlparse(request_URL)
    path = parsed_URL.path
    if path != "" and path[-1] != "/":  # ensure the path ends in a /
        path += "/"
    path += FULL_PAYLOAD.decode('utf-8')  # the path must be a string while the payload is bytes
    url = parsed_URL._replace(path=path).geturl()
    body = requests.get(url, cookies=cookies).text.lower()
    xss_info = get_XSS_data(body, url, "End of URL")
    sqli_info = get_SQLi_data(body, original_body, url, "End of URL")
    return xss_info, sqli_info


def test_referer_injection(original_body: str, request_URL: str, cookies: Cookies) -> VulnData:
    """ Test the given URL for XSS via injection into the referer and
        log the XSS if found """
    body = requests.get(request_URL, headers={'referer': FULL_PAYLOAD}, cookies=cookies).text.lower()
    xss_info = get_XSS_data(body, request_URL, "Referer")
    sqli_info = get_SQLi_data(body, original_body, request_URL, "Referer")
    return xss_info, sqli_info


def test_user_agent_injection(original_body: str, request_URL: str, cookies: Cookies) -> VulnData:
    """ Test the given URL for XSS via injection into the user agent and
        log the XSS if found """
    body = requests.get(request_URL, headers={'User-Agent': FULL_PAYLOAD}, cookies=cookies).text.lower()
    xss_info = get_XSS_data(body, request_URL, "User Agent")
    sqli_info = get_SQLi_data(body, original_body, request_URL, "User Agent")
    return xss_info, sqli_info


def test_query_injection(original_body: str, request_URL: str, cookies: Cookies):
    """ Test the given URL for XSS via injection into URL queries and
        log the XSS if found """
    parsed_URL = urlparse(request_URL)
    query_string = parsed_URL.query
    # queries is a list of parameters where each parameter is set to the payload
    queries = [query.split("=")[0] + "=" + FULL_PAYLOAD.decode('utf-8') for query in query_string.split("&")]
    new_query_string = "&".join(queries)
    new_URL = parsed_URL._replace(query=new_query_string).geturl()
    body = requests.get(new_URL, cookies=cookies).text.lower()
    xss_info = get_XSS_data(body, new_URL, "Query")
    sqli_info = get_SQLi_data(body, original_body, new_URL, "Query")
    return xss_info, sqli_info


def log_XSS_data(xss_info: Optional[XSSData]) -> None:
    """ Log information about the given XSS to mitmproxy """
    # If it is None, then there is no info to log
    if not xss_info:
        return
    ctx.log.error("===== XSS Found ====")
    ctx.log.error("XSS URL: %s" % xss_info.url)
    ctx.log.error("Injection Point: %s" % xss_info.injection_point)
    ctx.log.error("Suggested Exploit: %s" % xss_info.exploit)
    ctx.log.error("Line: %s" % xss_info.line)


def log_SQLi_data(sqli_info: Optional[SQLiData]) -> None:
    """ Log information about the given SQLi to mitmproxy """
    if not sqli_info:
        return
    ctx.log.error("===== SQLi Found =====")
    ctx.log.error("SQLi URL: %s" % sqli_info.url)
    ctx.log.error("Injection Point: %s" % sqli_info.injection_point)
    ctx.log.error("Regex used: %s" % sqli_info.regex)
    ctx.log.error("Suspected DBMS: %s" % sqli_info.dbms)
    return


def get_SQLi_data(new_body: str, original_body: str, request_URL: str, injection_point: str) -> Optional[SQLiData]:
    """ Return a SQLiDict if there is a SQLi otherwise return None
        String String URL String -> (SQLiDict or None) """
    # Regexes taken from Damn Small SQLi Scanner: https://github.com/stamparm/DSSS/blob/master/dsss.py#L17
    DBMS_ERRORS = {
        "MySQL": (r"SQL syntax.*MySQL", r"Warning.*mysql_.*", r"valid MySQL result", r"MySqlClient\."),
        "PostgreSQL": (r"PostgreSQL.*ERROR", r"Warning.*\Wpg_.*", r"valid PostgreSQL result", r"Npgsql\."),
        "Microsoft SQL Server": (r"Driver.* SQL[\-\_\ ]*Server", r"OLE DB.* SQL Server", r"(\W|\A)SQL Server.*Driver",
                                 r"Warning.*mssql_.*", r"(\W|\A)SQL Server.*[0-9a-fA-F]{8}",
                                 r"(?s)Exception.*\WSystem\.Data\.SqlClient\.", r"(?s)Exception.*\WRoadhouse\.Cms\."),
        "Microsoft Access": (r"Microsoft Access Driver", r"JET Database Engine", r"Access Database Engine"),
        "Oracle": (r"\bORA-[0-9][0-9][0-9][0-9]", r"Oracle error", r"Oracle.*Driver", r"Warning.*\Woci_.*", r"Warning.*\Wora_.*"),
        "IBM DB2": (r"CLI Driver.*DB2", r"DB2 SQL error", r"\bdb2_\w+\("),
        "SQLite": (r"SQLite/JDBCDriver", r"SQLite.Exception", r"System.Data.SQLite.SQLiteException", r"Warning.*sqlite_.*",
                   r"Warning.*SQLite3::", r"\[SQLITE_ERROR\]"),
        "Sybase": (r"(?i)Warning.*sybase.*", r"Sybase message", r"Sybase.*Server message.*"),
    }
    for dbms, regexes in DBMS_ERRORS.items():
        for regex in regexes:  # type: ignore
            if re.search(regex, new_body, re.IGNORECASE) and not re.search(regex, original_body, re.IGNORECASE):
                return SQLiData(request_URL,
                                injection_point,
                                regex,
                                dbms)
    return None


# A qc is either ' or "
def inside_quote(qc: str, substring_bytes: bytes, text_index: int, body_bytes: bytes) -> bool:
    """ Whether the Numberth occurrence of the first string in the second
        string is inside quotes as defined by the supplied QuoteChar """
    substring = substring_bytes.decode('utf-8')
    body = body_bytes.decode('utf-8')
    num_substrings_found = 0
    in_quote = False
    for index, char in enumerate(body):
        # Whether the next chunk of len(substring) chars is the substring
        next_part_is_substring = (
            (not (index + len(substring) > len(body))) and
            (body[index:index + len(substring)] == substring)
        )
        # Whether this char is escaped with a \
        is_not_escaped = (
            (index - 1 < 0 or index - 1 > len(body)) or
            (body[index - 1] != "\\")
        )
        if char == qc and is_not_escaped:
            in_quote = not in_quote
        if next_part_is_substring:
            if num_substrings_found == text_index:
                return in_quote
            num_substrings_found += 1
    return False


def paths_to_text(html: str, string: str) -> List[str]:
    """ Return list of Paths to a given str in the given HTML tree
          - Note that it does a BFS """

    def remove_last_occurence_of_sub_string(string: str, substr: str) -> str:
        """ Delete the last occurrence of substr from str
        String String -> String
        """
        index = string.rfind(substr)
        return string[:index] + string[index + len(substr):]

    class PathHTMLParser(HTMLParser):
        currentPath = ""
        paths: List[str] = []

        def handle_starttag(self, tag, attrs):
            self.currentPath += ("/" + tag)

        def handle_endtag(self, tag):
            self.currentPath = remove_last_occurence_of_sub_string(self.currentPath, "/" + tag)

        def handle_data(self, data):
            if string in data:
                self.paths.append(self.currentPath)

    parser = PathHTMLParser()
    parser.feed(html)
    return parser.paths


def get_XSS_data(body: Union[str, bytes], request_URL: str, injection_point: str) -> Optional[XSSData]:
    """ Return a XSSDict if there is a XSS otherwise return None """
    def in_script(text, index, body) -> bool:
        """ Whether the Numberth occurrence of the first string in the second
            string is inside a script tag """
        paths = paths_to_text(body.decode('utf-8'), text.decode("utf-8"))
        try:
            path = paths[index]
            return "script" in path
        except IndexError:
            return False

    def in_HTML(text: bytes, index: int, body: bytes) -> bool:
        """ Whether the Numberth occurrence of the first string in the second
            string is inside the HTML but not inside a script tag or part of
            a HTML attribute"""
        # if there is a < then lxml will interpret that as a tag, so only search for the stuff before it
        text = text.split(b"<")[0]
        paths = paths_to_text(body.decode('utf-8'), text.decode("utf-8"))
        try:
            path = paths[index]
            return "script" not in path
        except IndexError:
            return False

    def inject_javascript_handler(html: str) -> bool:
        """ Whether you can inject a Javascript:alert(0) as a link """
        class injectJSHandlerHTMLParser(HTMLParser):
            injectJSHandler = False

            def handle_starttag(self, tag, attrs):
                for name, value in attrs:
                    if name == "href" and value.startswith(FRONT_WALL.decode('utf-8')):
                        self.injectJSHandler = True

        parser = injectJSHandlerHTMLParser()
        parser.feed(html)
        return parser.injectJSHandler
    # Only convert the body to bytes if needed
    if isinstance(body, str):
        body = bytes(body, 'utf-8')
    # Regex for between 24 and 72 (aka 24*3) characters encapsulated by the walls
    regex = re.compile(b"""%s.{24,72}?%s""" % (FRONT_WALL, BACK_WALL))
    matches = regex.findall(body)
    for index, match in enumerate(matches):
        # Where the string is injected into the HTML
        in_script_val = in_script(match, index, body)
        in_HTML_val = in_HTML(match, index, body)
        in_tag = not in_script_val and not in_HTML_val
        in_single_quotes = inside_quote("'", match, index, body)
        in_double_quotes = inside_quote('"', match, index, body)
        # Whether you can inject:
        inject_open_angle = b"ao<ac" in match  # open angle brackets
        inject_close_angle = b"ac>so" in match  # close angle brackets
        inject_single_quotes = b"s'd" in match  # single quotes
        inject_double_quotes = b'd"ao' in match  # double quotes
        inject_slash = b"sl/bsl" in match  # forward slashes
        inject_semi = b"se;sl" in match  # semicolons
        inject_equals = b"eq=" in match  # equals sign
        if in_script_val and inject_slash and inject_open_angle and inject_close_angle:  # e.g. <script>PAYLOAD</script>
            return XSSData(request_URL,
                           injection_point,
                           '</script><script>alert(0)</script><script>',
                           match.decode('utf-8'))
        elif in_script_val and in_single_quotes and inject_single_quotes and inject_semi:  # e.g. <script>t='PAYLOAD';</script>
            return XSSData(request_URL,
                           injection_point,
                           "';alert(0);g='",
                           match.decode('utf-8'))
        elif in_script_val and in_double_quotes and inject_double_quotes and inject_semi:  # e.g. <script>t="PAYLOAD";</script>
            return XSSData(request_URL,
                           injection_point,
                           '";alert(0);g="',
                           match.decode('utf-8'))
        elif in_tag and in_single_quotes and inject_single_quotes and inject_open_angle and inject_close_angle and inject_slash:
            # e.g. <a href='PAYLOAD'>Test</a>
            return XSSData(request_URL,
                           injection_point,
                           "'><script>alert(0)</script>",
                           match.decode('utf-8'))
        elif in_tag and in_double_quotes and inject_double_quotes and inject_open_angle and inject_close_angle and inject_slash:
            # e.g. <a href="PAYLOAD">Test</a>
            return XSSData(request_URL,
                           injection_point,
                           '"><script>alert(0)</script>',
                           match.decode('utf-8'))
        elif in_tag and not in_double_quotes and not in_single_quotes and inject_open_angle and inject_close_angle and inject_slash:
            # e.g. <a href=PAYLOAD>Test</a>
            return XSSData(request_URL,
                           injection_point,
                           '><script>alert(0)</script>',
                           match.decode('utf-8'))
        elif inject_javascript_handler(body.decode('utf-8')):  # e.g. <html><a href=PAYLOAD>Test</a>
            return XSSData(request_URL,
                           injection_point,
                           'Javascript:alert(0)',
                           match.decode('utf-8'))
        elif in_tag and in_double_quotes and inject_double_quotes and inject_equals:  # e.g. <a href="PAYLOAD">Test</a>
            return XSSData(request_URL,
                           injection_point,
                           '" onmouseover="alert(0)" t="',
                           match.decode('utf-8'))
        elif in_tag and in_single_quotes and inject_single_quotes and inject_equals:  # e.g. <a href='PAYLOAD'>Test</a>
            return XSSData(request_URL,
                           injection_point,
                           "' onmouseover='alert(0)' t='",
                           match.decode('utf-8'))
        elif in_tag and not in_single_quotes and not in_double_quotes and inject_equals:  # e.g. <a href=PAYLOAD>Test</a>
            return XSSData(request_URL,
                           injection_point,
                           " onmouseover=alert(0) t=",
                           match.decode('utf-8'))
        elif in_HTML_val and not in_script_val and inject_open_angle and inject_close_angle and inject_slash:  # e.g. <html>PAYLOAD</html>
            return XSSData(request_URL,
                           injection_point,
                           '<script>alert(0)</script>',
                           match.decode('utf-8'))
        else:
            return None
    return None


# response is mitmproxy's entry point
def response(flow: http.HTTPFlow) -> None:
    assert flow.response
    cookies_dict = get_cookies(flow)
    resp = flow.response.get_text(strict=False)
    assert resp
    # Example: http://xss.guru/unclaimedScriptTag.html
    find_unclaimed_URLs(resp, flow.request.url)
    results = test_end_of_URL_injection(resp, flow.request.url, cookies_dict)
    log_XSS_data(results[0])
    log_SQLi_data(results[1])
    # Example: https://daviddworken.com/vulnerableReferer.php
    results = test_referer_injection(resp, flow.request.url, cookies_dict)
    log_XSS_data(results[0])
    log_SQLi_data(results[1])
    # Example: https://daviddworken.com/vulnerableUA.php
    results = test_user_agent_injection(resp, flow.request.url, cookies_dict)
    log_XSS_data(results[0])
    log_SQLi_data(results[1])
    if "?" in flow.request.url:
        # Example: https://daviddworken.com/vulnerable.php?name=
        results = test_query_injection(resp, flow.request.url, cookies_dict)
        log_XSS_data(results[0])
        log_SQLi_data(results[1])
