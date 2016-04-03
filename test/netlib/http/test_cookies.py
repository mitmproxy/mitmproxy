from netlib.http import cookies
from netlib.tutils import raises


def test_read_token():
    tokens = [
        [("foo", 0), ("foo", 3)],
        [("foo", 1), ("oo", 3)],
        [(" foo", 1), ("foo", 4)],
        [(" foo;", 1), ("foo", 4)],
        [(" foo=", 1), ("foo", 4)],
        [(" foo=bar", 1), ("foo", 4)],
    ]
    for q, a in tokens:
        assert cookies._read_token(*q) == a


def test_read_quoted_string():
    tokens = [
        [('"foo" x', 0), ("foo", 5)],
        [('"f\oo" x', 0), ("foo", 6)],
        [(r'"f\\o" x', 0), (r"f\o", 6)],
        [(r'"f\\" x', 0), (r"f" + '\\', 5)],
        [('"fo\\\"" x', 0), ("fo\"", 6)],
        [('"foo" x', 7), ("", 8)],
    ]
    for q, a in tokens:
        assert cookies._read_quoted_string(*q) == a


def test_read_pairs():
    vals = [
        [
            "one",
            [["one", None]]
        ],
        [
            "one=two",
            [["one", "two"]]
        ],
        [
            "one=",
            [["one", ""]]
        ],
        [
            'one="two"',
            [["one", "two"]]
        ],
        [
            'one="two"; three=four',
            [["one", "two"], ["three", "four"]]
        ],
        [
            'one="two"; three=four; five',
            [["one", "two"], ["three", "four"], ["five", None]]
        ],
        [
            'one="\\"two"; three=four',
            [["one", '"two'], ["three", "four"]]
        ],
    ]
    for s, lst in vals:
        ret, off = cookies._read_pairs(s)
        assert ret == lst


def test_pairs_roundtrips():
    pairs = [
        [
            "",
            []
        ],
        [
            "one=uno",
            [["one", "uno"]]
        ],
        [
            "one",
            [["one", None]]
        ],
        [
            "one=uno; two=due",
            [["one", "uno"], ["two", "due"]]
        ],
        [
            'one="uno"; two="\due"',
            [["one", "uno"], ["two", "due"]]
        ],
        [
            'one="un\\"o"',
            [["one", 'un"o']]
        ],
        [
            'one="uno,due"',
            [["one", 'uno,due']]
        ],
        [
            "one=uno; two; three=tre",
            [["one", "uno"], ["two", None], ["three", "tre"]]
        ],
        [
            "_lvs2=zHai1+Hq+Tc2vmc2r4GAbdOI5Jopg3EwsdUT9g=; "
            "_rcc2=53VdltWl+Ov6ordflA==;",
            [
                ["_lvs2", "zHai1+Hq+Tc2vmc2r4GAbdOI5Jopg3EwsdUT9g="],
                ["_rcc2", "53VdltWl+Ov6ordflA=="]
            ]
        ]
    ]
    for s, lst in pairs:
        ret, off = cookies._read_pairs(s)
        assert ret == lst
        s2 = cookies._format_pairs(lst)
        ret, off = cookies._read_pairs(s2)
        assert ret == lst


def test_cookie_roundtrips():
    pairs = [
        [
            "one=uno",
            [["one", "uno"]]
        ],
        [
            "one=uno; two=due",
            [["one", "uno"], ["two", "due"]]
        ],
    ]
    for s, lst in pairs:
        ret = cookies.parse_cookie_header(s)
        assert ret.lst == lst
        s2 = cookies.format_cookie_header(ret)
        ret = cookies.parse_cookie_header(s2)
        assert ret.lst == lst


def test_parse_set_cookie_pairs():
    pairs = [
        [
            "one=uno",
            [
                ["one", "uno"]
            ]
        ],
        [
            "one=un\x20",
            [
                ["one", "un\x20"]
            ]
        ],
        [
            "one=uno; foo",
            [
                ["one", "uno"],
                ["foo", None]
            ]
        ],
        [
            "mun=1.390.f60; "
            "expires=sun, 11-oct-2015 12:38:31 gmt; path=/; "
            "domain=b.aol.com",
            [
                ["mun", "1.390.f60"],
                ["expires", "sun, 11-oct-2015 12:38:31 gmt"],
                ["path", "/"],
                ["domain", "b.aol.com"]
            ]
        ],
        [
            r'rpb=190%3d1%2616726%3d1%2634832%3d1%2634874%3d1; '
            'domain=.rubiconproject.com; '
            'expires=mon, 11-may-2015 21:54:57 gmt; '
            'path=/',
            [
                ['rpb', r'190%3d1%2616726%3d1%2634832%3d1%2634874%3d1'],
                ['domain', '.rubiconproject.com'],
                ['expires', 'mon, 11-may-2015 21:54:57 gmt'],
                ['path', '/']
            ]
        ],
    ]
    for s, lst in pairs:
        ret = cookies._parse_set_cookie_pairs(s)
        assert ret == lst
        s2 = cookies._format_set_cookie_pairs(ret)
        ret2 = cookies._parse_set_cookie_pairs(s2)
        assert  ret2 == lst


def test_parse_set_cookie_header():
    vals = [
        [
            "", None
        ],
        [
            ";", None
        ],
        [
            "one=uno",
            ("one", "uno", [])
        ],
        [
            "one=uno; foo=bar",
            ("one", "uno", [["foo", "bar"]])
        ]
    ]
    for s, expected in vals:
        ret = cookies.parse_set_cookie_header(s)
        if expected:
            assert ret[0] == expected[0]
            assert ret[1] == expected[1]
            assert ret[2].lst == expected[2]
            s2 = cookies.format_set_cookie_header(*ret)
            ret2 = cookies.parse_set_cookie_header(s2)
            assert ret2[0] == expected[0]
            assert ret2[1] == expected[1]
            assert ret2[2].lst == expected[2]
        else:
            assert ret is None


def test_refresh_cookie():

    # Invalid expires format, sent to us by Reddit.
    c = "rfoo=bar; Domain=reddit.com; expires=Thu, 31 Dec 2037 23:59:59 GMT; Path=/"
    assert cookies.refresh_set_cookie_header(c, 60)

    c = "MOO=BAR; Expires=Tue, 08-Mar-2011 00:20:38 GMT; Path=foo.com; Secure"
    assert "00:21:38" in cookies.refresh_set_cookie_header(c, 60)

    # https://github.com/mitmproxy/mitmproxy/issues/773
    c = ">=A"
    with raises(ValueError):
        cookies.refresh_set_cookie_header(c, 60)