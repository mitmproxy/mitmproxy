from mitmproxy import ctx
from socket import gaierror, gethostbyname
from urllib.parse import urlparse
import requests
import re
from html.parser import HTMLParser

# The actual payload is put between a frontWall and a backWall to make it easy
# to locate the payload with regular expressions
FRONT_WALL = b"1029zxc"
BACK_WALL = b"3847asd"
PAYLOAD = b"""s'd"ao<ac>so[sb]po(pc)se;sl/bsl\\eq="""
FULL_PAYLOAD = FRONT_WALL + PAYLOAD + BACK_WALL

# A URL is a string starting with http:// or https:// that points to a website
# A XSSDict is a dictionary with the following keys value pairs:
#   - 'URL' -> URL
#   - 'Injection Point' -> String
#   - 'Exploit' -> String
#   - 'Line' -> String
# A SQLiDict is a dictionary with the following keys value pairs:
#   - 'URL' -> URL
#   - 'Injection Point' -> String
#   - 'Regex' -> String
#   - 'DBMS' -> String


def get_cookies(flow):
    """ Return a dict going from cookie names to cookie values
          - Note that it includes both the cookies sent in the original request and
            the cookies sent by the server
        Flow -> Dict """
    return {name: value for name, value in flow.request.cookies.fields}


def find_unclaimed_URLs(body, requestUrl):
    """ Look for unclaimed URLs in script tags and log them if found
        String URL -> None """
    class ScriptURLExtractor(HTMLParser):
        script_URLs = []

        def handle_starttag(self, tag, attrs):
            if tag == "script" and "src" in [name for name, value in attrs]:
                for name, value in attrs:
                    if name == "src":
                        self.script_URLs.append(value)

    parser = ScriptURLExtractor()
    try:
        parser.feed(body)
    except TypeError:
        parser.feed(body.decode('utf-8'))
    for url in parser.script_URLs:
        parser = urlparse(url)
        domain = parser.netloc
        try:
            gethostbyname(domain)
        except gaierror:
            ctx.log.error("XSS found in %s due to unclaimed URL \"%s\" in script tag." % (requestUrl, url))


def test_end_of_URL_injection(originalBody, requestURL, cookies):
    """ Test the given URL for XSS via injection onto the end of the URL and
        log the XSS if found
        URL -> XSSDict """
    parsed_URL = urlparse(requestURL)
    path = parsed_URL.path
    if path != "" and path[-1] != "/":  # ensure the path ends in a /
        path += "/"
    path += FULL_PAYLOAD.decode('utf-8')  # the path must be a string while the payload is bytes
    url = parsed_URL._replace(path=path).geturl()
    body = requests.get(url, cookies=cookies).text.lower()
    xss_info = get_XSS_data(body, url, "End of URL")
    sqli_info = get_SQLi_data(body, originalBody, url, "End of URL")
    return xss_info, sqli_info


def test_referer_injection(originalBody, requestURL, cookies):
    """ Test the given URL for XSS via injection into the referer and
        log the XSS if found
        URL -> XSSDict """
    body = requests.get(requestURL, headers={'referer': FULL_PAYLOAD}, cookies=cookies).text.lower()
    xss_info = get_XSS_data(body, requestURL, "Referer")
    sqli_info = get_SQLi_data(body, originalBody, requestURL, "Referer")
    return xss_info, sqli_info


def test_user_agent_injection(originalBody, requestURL, cookies):
    """ Test the given URL for XSS via injection into the user agent and
        log the XSS if found
        URL -> XSSDict """
    body = requests.get(requestURL, headers={'User-Agent': FULL_PAYLOAD}, cookies=cookies).text.lower()
    xss_info = get_XSS_data(body, requestURL, "User Agent")
    sqli_info = get_SQLi_data(body, originalBody, requestURL, "User Agent")
    return xss_info, sqli_info


def test_query_injection(originalBody, requestURL, cookies):
    """ Test the given URL for XSS via injection into URL queries and
        log the XSS if found
        URL -> XSSDict """
    parsed_URL = urlparse(requestURL)
    query_string = parsed_URL.query
    # queries is a list of parameters where each parameter is set to the payload
    queries = [query.split("=")[0] + "=" + FULL_PAYLOAD.decode('utf-8') for query in query_string.split("&")]
    new_query_string = "&".join(queries)
    new_URL = parsed_URL._replace(query=new_query_string).geturl()
    body = requests.get(new_URL, cookies=cookies).text.lower()
    xss_info = get_XSS_data(body, new_URL, "Query")
    sqli_info = get_SQLi_data(body, originalBody, new_URL, "Query")
    return xss_info, sqli_info


def log_XSS_data(xss_info):
    """ Log information about the given XSS to mitmproxy
        (XSSDict or None) -> None """
    # If it is None, then there is no info to log
    if not xss_info:
        return
    ctx.log.error("===== XSS Found ====")
    ctx.log.error("XSS URL: %s" % xss_info['URL'])
    ctx.log.error("Injection Point: %s" % xss_info['Injection Point'])
    ctx.log.error("Suggested Exploit: %s" % xss_info['Exploit'])
    ctx.log.error("Line: %s" % xss_info['Line'])


def log_SQLi_data(sqli_info):
    """ Log information about the given SQLi to mitmproxy
        (SQLiDict or None) -> None """
    if not sqli_info:
        return
    ctx.log.error("===== SQLi Found =====")
    ctx.log.error("SQLi URL: %s" % sqli_info['URL'])
    ctx.log.error("Injection Point: %s" % sqli_info['Injection Point'])
    ctx.log.error("Regex used: %s" % sqli_info['Regex'])


def get_SQLi_data(new_body, original_body, request_URL, injection_point):
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
        for regex in regexes:
            if re.search(regex, new_body) and not re.search(regex, original_body):
                return {'URL': request_URL,
                        'Injection Point': injection_point,
                        'Regex': regex,
                        'DBMS': dbms}


# A QuoteChar is either ' or "
def inside_quote(qc, substring, text_index, body):
    """ Whether the Numberth occurence of the first string in the second
        string is inside quotes as defined by the supplied QuoteChar
        QuoteChar String Number String -> Boolean """
    def next_part_is_substring(index):
        if index + len(substring) > len(body):
            return False
        return body[index:index + len(substring)] == substring

    def is_not_escaped(index):
        if index - 1 < 0 or index - 1 > len(body):
            return True
        return body[index - 1] != "\\"

    substring = substring.decode('utf-8')
    body = body.decode('utf-8')
    num_substrings_found = 0
    in_quote = False
    for index, char in enumerate(body):
        if char == qc and is_not_escaped(index):
            in_quote = not in_quote
        if next_part_is_substring(index):
            if num_substrings_found == text_index:
                return in_quote
            num_substrings_found += 1
    return False


# An HTML is a String containing valid HTML
def paths_to_text(html, str):
    """ Return list of Paths to a given str in the given HTML tree
          - Note that it does a BFS
        HTML String -> [ListOf Path] """

    def remove_last_occurence_of_sub_string(str, substr):
        """ Delete the last occurence of substr from str
        String String -> String
        """
        index = str.rfind(substr)
        return str[:index] + str[index + len(substr):]

    class PathHTMLParser(HTMLParser):
        currentPath = ""
        paths = []

        def handle_starttag(self, tag, attrs):
            self.currentPath += ("/" + tag)

        def handle_endtag(self, tag):
            self.currentPath = remove_last_occurence_of_sub_string(self.currentPath, "/" + tag)

        def handle_data(self, data):
            if str in data:
                self.paths.append(self.currentPath)

    parser = PathHTMLParser()
    parser.feed(html)
    return parser.paths


def get_XSS_data(body, request_URL, injection_point):
    """ Return a XSSDict if there is a XSS otherwise return None
        String URL String -> (XSSDict or None) """
    def in_script(text, index, body):
        """ Whether the Numberth occurence of the first string in the second
            string is inside a script tag
            String Number String -> Boolean """
        paths = paths_to_text(body.decode('utf-8'), text.decode("utf-8"))
        try:
            path = paths[index]
            return "script" in path
        except IndexError:
            return False

    def in_HTML(text, index, body):
        """ Whether the Numberth occurence of the first string in the second
            string is inside the HTML but not inside a script tag or part of
            a HTML attribute
            String Number String -> Boolean """
        # if there is a < then lxml will interpret that as a tag, so only search for the stuff before it
        text = text.split(b"<")[0]
        paths = paths_to_text(body.decode('utf-8'), text.decode("utf-8"))
        try:
            path = paths[index]
            return "script" not in path
        except IndexError:
            return False

    def inject_javascript_handler(html):
        """ Whether you can inject a Javascript:alert(0) as a link
            [ListOf HTMLTree] -> Boolean """
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
        in_script = in_script(match, index, body)
        in_HTML = in_HTML(match, index, body)
        in_tag = not in_script and not in_HTML
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
        # The initial response dict:
        respDict = {'Line': match.decode('utf-8'),
                    'URL': request_URL,
                    'Injection Point': injection_point}
        if in_script and inject_slash and inject_open_angle and inject_close_angle:  # e.g. <script>PAYLOAD</script>
            respDict['Exploit'] = '</script><script>alert(0)</script><script>'
            return respDict
        elif in_script and in_single_quotes and inject_single_quotes and inject_semi:  # e.g. <script>t='PAYLOAD';</script>
            respDict['Exploit'] = "';alert(0);g='"
            return respDict
        elif in_script and in_double_quotes and inject_double_quotes and inject_semi:  # e.g. <script>t="PAYLOAD";</script>
            respDict['Exploit'] = '";alert(0);g="'
            return respDict
        elif in_tag and in_single_quotes and inject_single_quotes and inject_open_angle and inject_close_angle and inject_slash:
            # e.g. <a href='PAYLOAD'>Test</a>
            respDict['Exploit'] = "'><script>alert(0)</script>"
            return respDict
        elif in_tag and in_double_quotes and inject_double_quotes and inject_open_angle and inject_close_angle and inject_slash:
            # e.g. <a href="PAYLOAD">Test</a>
            respDict['Exploit'] = '"><script>alert(0)</script>'
            return respDict
        elif in_tag and not in_double_quotes and not in_single_quotes and inject_open_angle and inject_close_angle and inject_slash:
            # e.g. <a href=PAYLOAD>Test</a>
            respDict['Exploit'] = '><script>alert(0)</script>'
            return respDict
        elif inject_javascript_handler(body.decode('utf-8')):  # e.g. <html><a href=PAYLOAD>Test</a>
            respDict['Exploit'] = 'Javascript:alert(0)'
            return respDict
        elif in_tag and in_double_quotes and inject_double_quotes and inject_equals:  # e.g. <a href="PAYLOAD">Test</a>
            respDict['Exploit'] = '" onmouseover="alert(0)" t="'
            return respDict
        elif in_tag and in_single_quotes and inject_single_quotes and inject_equals:  # e.g. <a href='PAYLOAD'>Test</a>
            respDict['Exploit'] = "' onmouseover='alert(0)' t='"
            return respDict
        elif in_tag and not in_single_quotes and not in_double_quotes and inject_equals:  # e.g. <a href=PAYLOAD>Test</a>
            respDict['Exploit'] = " onmouseover=alert(0) t="
            return respDict
        elif in_HTML and not in_script and inject_open_angle and inject_close_angle and inject_slash:  # e.g. <html>PAYLOAD</html>
            respDict['Exploit'] = '<script>alert(0)</script>'
            return respDict
        else:
            return None


# response is mitmproxy's entry point
def response(flow):
    cookiesDict = get_cookies(flow)
    # Example: http://xss.guru/unclaimedScriptTag.html
    log_XSS_data(find_unclaimed_URLs(flow.response.content, flow.request.url))
    results = test_end_of_URL_injection(flow.response.content, flow.request.url, cookiesDict)
    log_XSS_data(results[0])
    log_SQLi_data(results[1])
    # Example: https://daviddworken.com/vulnerableReferer.php
    results = test_referer_injection(flow.response.content, flow.request.url, cookiesDict)
    log_XSS_data(results[0])
    log_SQLi_data(results[1])
    # Example: https://daviddworken.com/vulnerableUA.php
    results = test_user_agent_injection(flow.response.content, flow.request.url, cookiesDict)
    log_XSS_data(results[0])
    log_SQLi_data(results[1])
    if "?" in flow.request.url:
        # Example: https://daviddworken.com/vulnerable.php?name=
        results = test_query_injection(flow.response.content, flow.request.url, cookiesDict)
        log_XSS_data(results[0])
        log_SQLi_data(results[1])
