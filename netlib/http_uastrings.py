from __future__ import (absolute_import, print_function, division)

"""
    A small collection of useful user-agent header strings. These should be
    kept reasonably current to reflect common usage.
"""

# pylint: line-too-long

# A collection of (name, shortcut, string) tuples.

UASTRINGS = [
    ("android",
     "a",
     "Mozilla/5.0 (Linux; U; Android 4.1.1; en-gb; Nexus 7 Build/JRO03D) AFL/01.04.02"),  # noqa
    ("blackberry",
     "l",
     "Mozilla/5.0 (BlackBerry; U; BlackBerry 9900; en) AppleWebKit/534.11+ (KHTML, like Gecko) Version/7.1.0.346 Mobile Safari/534.11+"),  # noqa
    ("bingbot",
     "b",
     "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"),  # noqa
    ("chrome",
     "c",
     "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1"),  # noqa
    ("firefox",
     "f",
     "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:14.0) Gecko/20120405 Firefox/14.0a1"),  # noqa
    ("googlebot",
     "g",
     "Googlebot/2.1 (+http://www.googlebot.com/bot.html)"),  # noqa
    ("ie9",
     "i",
     "Mozilla/5.0 (Windows; U; MSIE 9.0; WIndows NT 9.0; en-US)"),  # noqa
    ("ipad",
     "p",
     "Mozilla/5.0 (iPad; CPU OS 5_1 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9B176 Safari/7534.48.3"),  # noqa
    ("iphone",
     "h",
     "Mozilla/5.0 (iPhone; CPU iPhone OS 4_2_1 like Mac OS X) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8C148a Safari/6533.18.5"),  # noqa
    ("safari",
     "s",
     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/534.55.3 (KHTML, like Gecko) Version/5.1.3 Safari/534.53.10"),  # noqa
]


def get_by_shortcut(s):
    """
        Retrieve a user agent entry by shortcut.
    """
    for i in UASTRINGS:
        if s == i[1]:
            return i
