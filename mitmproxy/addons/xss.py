from mitmproxy import ctx  # Used for logging information to mitmproxy
from socket import gaierror, gethostbyname  # Used to check whether a domain name resolves
from urllib.parse import urlparse  # Used to modify paths and queries for URLs
import requests  # Used to send additional requests when looking for XSSs
import re  # Used for pulling out the payload
from html.parser import HTMLParser  # used for parsing HTML

# The actual payload is put between a frontWall and a backWall to make it easy
# to locate the payload with regular expressions
frontWall = b"1029zxc"
backWall = b"3847asd"
payload = b"""s'd"ao<ac>so[sb]po(pc)se;sl/bsl\\"""
fullPayload = frontWall + payload + backWall

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


def getCookies(flow):
    """ Return a dict going from cookie names to cookie values
          - Note that it includes both the cookies sent in the original request and
            the cookies sent by the server
        Flow -> Dict """
    # responseCookies is a list of tuples going from the cookie name to a SetCookie object
    responseCookies = flow.response.cookies.fields
    # requestCookies is a list of tuples going from the cookie name to the value
    requestCookies = flow.request.cookies.fields
    cookieDict = {}
    for name, SC in responseCookies:
        cookieDict[name] = SC.value
    for name, value in requestCookies:
        cookieDict[name] = value
    return cookieDict


def findUnclaimedURLs(body, requestUrl):
    """ Look for unclaimed URLs in script tags and log them if found
        String URL -> None """
    class scriptURLExtractor(HTMLParser):
        scriptURLs = []

        def handle_starttag(self, tag, attrs):
            if tag == "script" and "src" in [name for name, value in attrs]:
                for name, value in attrs:
                    if name == "src":
                        self.scriptURLs.append(value)

    parser = scriptURLExtractor()
    parser.feed(body)
    for url in parser.scriptURLs:
        parser = urlparse(url)
        domain = parser.netloc
        try:
            gethostbyname(domain)
        except gaierror:
            ctx.log.error("XSS found in %s due to unclaimed URL \"%s\" in script tag." % (requestUrl, url))


def testEndOfURLInjection(originalBody, requestURL, cookies):
    """ Test the given URL for XSS via injection onto the end of the URL and
        log the XSS if found
        URL -> XSSDict """
    parsedURL = urlparse(requestURL)
    path = parsedURL.path
    if path[-1] != "/":  # ensure the path ends in a /
        path += "/"
    path += fullPayload.decode('utf-8')  # the path must be a string while the payload is bytes
    url = parsedURL._replace(path=path).geturl()
    body = requests.get(url, cookies=cookies).text.lower()
    xssInfo = getXSSInfo(body, url, "End of URL")
    sqliInfo = getSQLiInfo(body, originalBody, url, "End of URL")
    return xssInfo, sqliInfo


def testRefererInjection(originalBody, requestURL, cookies):
    """ Test the given URL for XSS via injection into the referer and
        log the XSS if found
        URL -> XSSDict """
    body = requests.get(requestURL, headers={'referer': fullPayload}, cookies=cookies).text.lower()
    xssInfo = getXSSInfo(body, requestURL, "Referer")
    sqliInfo = getSQLiInfo(body, originalBody, requestURL, "Referer")
    return xssInfo, sqliInfo


def testUserAgentInjection(originalBody, requestURL, cookies):
    """ Test the given URL for XSS via injection into the user agent and
        log the XSS if found
        URL -> XSSDict """
    body = requests.get(requestURL, headers={'User-Agent': fullPayload}, cookies=cookies).text.lower()
    xssInfo = getXSSInfo(body, requestURL, "User Agent")
    sqliInfo = getSQLiInfo(body, originalBody, requestURL, "User Agent")
    return xssInfo, sqliInfo


def testQueryInjection(originalBody, requestURL, cookies):
    """ Test the given URL for XSS via injection into URL queries and
        log the XSS if found
        URL -> XSSDict """
    parsedURL = urlparse(requestURL)
    queryString = parsedURL.query
    # queries is a list of parameters where each parameter is set to the payload
    queries = [query.split("=")[0] + "=" + fullPayload.decode('utf-8') for query in queryString.split("&")]
    newQueryString = "&".join(queries)
    newURL = parsedURL._replace(query=newQueryString).geturl()
    body = requests.get(newURL, cookies=cookies).text.lower()
    xssInfo = getXSSInfo(body, newURL, "Query")
    sqliInfo = getSQLiInfo(body, originalBody, newURL, "Query")
    return xssInfo, sqliInfo


def logXSS(xssInfo):
    """ Log information about the given XSS to mitmproxy
        (XSSDict or None) -> None """
    # If it is None, then there is no info to log
    if not xssInfo:
        return
    ctx.log.error("===== XSS Found ====")
    ctx.log.error("XSS URL: %s" % xssInfo['URL'])
    ctx.log.error("Injection Point: %s" % xssInfo['Injection Point'])
    ctx.log.error("Suggested Exploit: %s" % xssInfo['Exploit'])
    ctx.log.error("Line: %s" % xssInfo['Line'])


def logSQLiDict(SQLiDict):
    """ Log information about the given SQLi to mitmproxy
        (SQLiDict or None) -> None """
    if not SQLiDict:
        return
    ctx.log.error("===== SQLi Found =====")
    ctx.log.error("SQLi URL: %s" % SQLiDict['URL'])
    ctx.log.error("Injection Point: %s" % SQLiDict['Injection Point'])
    ctx.log.error("Regex used: %s" % SQLiDict['Regex'])


def getSQLiInfo(newBody, originalBody, requestURL, injectionPoint):
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
            if re.search(regex, newBody) and not re.search(regex, originalBody):
                return {'URL': requestURL,
                        'Injection Point': injectionPoint,
                        'Regex': regex,
                        'DBMS': dbms}


# A QuoteChar is either ' or "
def insideQuote(qc, substring, textIndex, body):
    """ Whether the Numberth occurence of the first string in the second
        string is inside quotes as defined by the supplied QuoteChar
        QuoteChar String Number String -> Boolean """
    def nextPartIsSubstring(index):
        if index + len(substring) > len(body):
            return False
        return body[index:index + len(substring)] == substring

    def isNotEscaped(index):
        if index - 1 < 0 or index - 1 > len(body):
            return True
        return body[index - 1] != "\\"

    substring = substring.decode('utf-8')
    body = body.decode('utf-8')
    numSubstringsFound = 0
    inQuote = False
    for index, char in enumerate(body):
        if char == qc and isNotEscaped(index):
            inQuote = not inQuote
        if nextPartIsSubstring(index):
            if numSubstringsFound == textIndex:
                return inQuote
            numSubstringsFound += 1
    return False


# An HTML is a String containing valid HTML
def pathsToText(html, str):
    """ Return list of Paths to a given str in the given HTML tree
          - Note that it does a BFS
        HTML String -> [ListOf Path] """

    def removeLastOccurenceOfSubString(str, substr):
        """ Delete the last occurence of substr from str
        String String -> String
        """
        index = str.rfind(substr)
        return str[:index] + str[index + len(substr):]

    class pathHTMLParser(HTMLParser):
        currentPath = ""
        paths = []

        def handle_starttag(self, tag, attrs):
            self.currentPath += ("/" + tag)

        def handle_endtag(self, tag):
            self.currentPath = removeLastOccurenceOfSubString(self.currentPath, "/" + tag)

        def handle_data(self, data):
            if str in data:
                self.paths.append(self.currentPath)

    parser = pathHTMLParser()
    parser.feed(html)
    return parser.paths


def getXSSInfo(body, requestURL, injectionPoint):
    """ Return a XSSDict if there is a XSS otherwise return None
        String URL String -> (XSSDict or None) """
    # All of the injection tests work by checking whether the character (with
    # the fences on the side) appear in the body of the HTML
    def injectOA(match):
        """ Whether or not you can inject <
            Bytes -> Boolean """
        return b"ao<ac" in match

    def injectCA(match):
        """ Whether or not you can inject >
            Bytes -> Boolean """
        return b"ac>so" in match

    def injectSingleQuotes(match):
        """ Whether or not you can inject '
            Bytes -> Boolean """
        return b"s'd" in match

    def injectDoubleQuotes(match):
        """ Whether or not you can inject "
            Bytes -> Boolean """
        return b'd"ao' in match

    def injectSlash(match):
        """ Whether or not you can inject /
            Bytes -> Boolean """
        return b"sl/bsl" in match

    def injectSemi(match):
        """ Whether or not you can inject ;
            Bytes -> Boolean """
        return b"se;sl" in match

    def inScript(text, index, body):
        """ Whether the Numberth occurence of the first string in the second
            string is inside a script tag
            String Number String -> Boolean """
        paths = pathsToText(body.decode('utf-8'), text.decode("utf-8"))
        try:
            path = paths[index]
            return "script" in path
        except IndexError:
            return False

    def inHTML(text, index, body):
        """ Whether the Numberth occurence of the first string in the second
            string is inside the HTML but not inside a script tag or part of
            a HTML attribute
            String Number String -> Boolean """
        # if there is a < then lxml will interpret that as a tag, so only search for the stuff before it
        text = text.split(b"<")[0]
        paths = pathsToText(body.decode('utf-8'), text.decode("utf-8"))
        try:
            path = paths[index]
            return "script" not in path
        except IndexError:
            return False

    def injectJavascriptHandler(html):
        """ Whether you can inject a Javascript:alert(0) as a link
            [ListOf HTMLTree] -> Boolean """
        class injectJSHandlerHTMLParser(HTMLParser):
            injectJSHandler = False

            def handle_starttag(self, tag, attrs):
                for name, value in attrs:
                    if name == "href" and value.startswith(frontWall.decode('utf-8')):
                        self.injectJSHandler = True

        parser = injectJSHandlerHTMLParser()
        parser.feed(html)
        return parser.injectJSHandler
    # Only convert the body to bytes if needed
    if isinstance(body, str):
        body = bytes(body, 'utf-8')
    # Regex for between 24 and 72 (aka 24*3) characters encapsulated by the walls
    regex = re.compile(b"""%s.{24,72}?%s""" % (frontWall, backWall))
    matches = regex.findall(body)
    for index, match in enumerate(matches):
        # Where the string is injected into the HTML
        inScript = inScript(match, index, body)
        inHTML = inHTML(match, index, body)
        inTag = not inScript and not inHTML
        inSingleQuotes = insideQuote("'", match, index, body)
        inDoubleQuotes = insideQuote('"', match, index, body)
        # Whether you can inject:
        injectOA = injectOA(match)  # open angle brackets
        injectCA = injectCA(match)  # close angle brackets
        injectSingleQuotes = injectSingleQuotes(match)  # single quotes
        injectDoubleQuotes = injectDoubleQuotes(match)  # double quotes
        injectSlash = injectSlash(match)  # forward slashes
        injectSemi = injectSemi(match)  # semicolons
        # The initial response dict:
        respDict = {'Line': match.decode('utf-8'),
                    'URL': requestURL,
                    'Injection Point': injectionPoint}
        # Debugging:
        # print("====================================")
        # print("In Script: %s" % inScript)
        # print("In HTML: %s" % inHTML)
        # print("In Tag: %s" % inTag)
        # print("inSingleQuotes: %s" % inSingleQuotes)
        # print("inDoubleQuotes: %s" % inDoubleQuotes)
        # print("injectOA: %s" % injectOA)
        # print("injectCA: %s" % injectCA)
        # print("injectSingleQuotes: %s" % injectSingleQuotes)
        # print("injectDoubleQuotes: %s" % injectDoubleQuotes)
        # print("injectSlash: %s" % injectSlash)
        # print("injectSemi: %s" % injectSemi)
        if inScript and injectSlash and injectOA and injectCA:  # e.g. <script>PAYLOAD</script>
            respDict['Exploit'] = '</script><script>alert(0)</script><script>'
            return respDict
        elif inScript and inSingleQuotes and injectSingleQuotes and injectSemi:  # e.g. <script>t='PAYLOAD';</script>
            respDict['Exploit'] = "';alert(0);g='"
            return respDict
        elif inScript and inDoubleQuotes and injectDoubleQuotes and injectSemi:  # e.g. <script>t="PAYLOAD";</script>
            respDict['Exploit'] = '";alert(0);g="'
            return respDict
        elif inTag and inSingleQuotes and injectSingleQuotes and injectOA and injectCA and injectSlash:  # e.g. <a href='PAYLOAD'>Test</a>
            respDict['Exploit'] = "'><script>alert(0)</script>"
            return respDict
        elif inTag and inDoubleQuotes and injectDoubleQuotes and injectOA and injectCA and injectSlash:  # e.g. <a href="PAYLOAD">Test</a>
            respDict['Exploit'] = '"><script>alert(0)</script>'
            return respDict
        elif inTag and not inDoubleQuotes and not inSingleQuotes and injectOA and injectCA and injectSlash:  # e.g. <a href=PAYLOAD>Test</a>
            respDict['Exploit'] = '><script>alert(0)</script>'
            return respDict
        elif inHTML and not inScript and injectOA and injectCA and injectSlash:  # e.g. <html>PAYLOAD</html>
            respDict['Exploit'] = '<script>alert(0)</script>'
            return respDict
        elif injectJavascriptHandler(body.decode('utf-8')):  # e.g. <html><a href=PAYLOAD>Test</a>
            respDict['Exploit'] = 'Javascript:alert(0)'
            return respDict
        # TODO: Injection of JS executing attributes (e.g. onmouseover)
        else:
            return None


# response is mitmproxy's entry point
def response(flow):
    cookiesDict = getCookies(flow)
    # Example: http://xss.guru/unclaimedScriptTag.html
    logXSS(findUnclaimedURLs(flow.response.content, flow.request.url))
    results = testEndOfURLInjection(flow.response.content, flow.request.url, cookiesDict)
    logXSS(results[0])
    logSQLiDict(results[1])
    # Example: https://daviddworken.com/vulnerableReferer.php
    results = testRefererInjection(flow.response.content, flow.request.url, cookiesDict)
    logXSS(results[0])
    logSQLiDict(results[1])
    # Example: https://daviddworken.com/vulnerableUA.php
    results = testUserAgentInjection(flow.response.content, flow.request.url, cookiesDict)
    logXSS(results[0])
    logSQLiDict(results[1])
    if "?" in flow.request.url:
        # Example: https://daviddworken.com/vulnerable.php?name=
        results = testQueryInjection(flow.response.content, flow.request.url, cookiesDict)
        logXSS(results[0])
        logSQLiDict(results[1])
