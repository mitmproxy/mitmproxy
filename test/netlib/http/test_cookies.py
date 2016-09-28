import time

from netlib.http import cookies
from netlib.tutils import raises

import mock

cookie_pairs = [
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


def test_read_key():
    tokens = [
        [("foo", 0), ("foo", 3)],
        [("foo", 1), ("oo", 3)],
        [(" foo", 0), (" foo", 4)],
        [(" foo", 1), ("foo", 4)],
        [(" foo;", 1), ("foo", 4)],
        [(" foo=", 1), ("foo", 4)],
        [(" foo=bar", 1), ("foo", 4)],
    ]
    for q, a in tokens:
        assert cookies._read_key(*q) == a


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


def test_read_cookie_pairs():
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
        ret, off = cookies._read_cookie_pairs(s)
        assert ret == lst


def test_pairs_roundtrips():
    for s, expected in cookie_pairs:
        ret, off = cookies._read_cookie_pairs(s)
        assert ret == expected

        s2 = cookies._format_pairs(expected)
        ret, off = cookies._read_cookie_pairs(s2)
        assert ret == expected


def test_cookie_roundtrips():
    for s, expected in cookie_pairs:
        ret = cookies.parse_cookie_header(s)
        assert ret == expected

        s2 = cookies.format_cookie_header(expected)
        ret = cookies.parse_cookie_header(s2)
        assert ret == expected


def test_parse_set_cookie_pairs():
    pairs = [
        [
            "one=uno",
            [[
                ["one", "uno"]
            ]]
        ],
        [
            "one=un\x20",
            [[
                ["one", "un\x20"]
            ]]
        ],
        [
            "one=uno; foo",
            [[
                ["one", "uno"],
                ["foo", None]
            ]]
        ],
        [
            "mun=1.390.f60; "
            "expires=sun, 11-oct-2015 12:38:31 gmt; path=/; "
            "domain=b.aol.com",
            [[
                ["mun", "1.390.f60"],
                ["expires", "sun, 11-oct-2015 12:38:31 gmt"],
                ["path", "/"],
                ["domain", "b.aol.com"]
            ]]
        ],
        [
            r'rpb=190%3d1%2616726%3d1%2634832%3d1%2634874%3d1; '
            'domain=.rubiconproject.com; '
            'expires=mon, 11-may-2015 21:54:57 gmt; '
            'path=/',
            [[
                ['rpb', r'190%3d1%2616726%3d1%2634832%3d1%2634874%3d1'],
                ['domain', '.rubiconproject.com'],
                ['expires', 'mon, 11-may-2015 21:54:57 gmt'],
                ['path', '/']
            ]]
        ],
    ]
    for s, expected in pairs:
        ret, off = cookies._read_set_cookie_pairs(s)
        assert ret == expected

        s2 = cookies._format_set_cookie_pairs(expected[0])
        ret2, off = cookies._read_set_cookie_pairs(s2)
        assert ret2 == expected


def test_parse_set_cookie_header():
    def set_cookie_equal(obs, exp):
        assert obs[0] == exp[0]
        assert obs[1] == exp[1]
        assert obs[2].items(multi=True) == exp[2]

    vals = [
        [
            "", []
        ],
        [
            ";", []
        ],
        [
            "one=uno",
            [
                ("one", "uno", ())
            ]
        ],
        [
            "one=uno; foo=bar",
            [
                ("one", "uno", (("foo", "bar"),))
            ]
        ],
        [
            "one=uno; foo=bar; foo=baz",
            [
                ("one", "uno", (("foo", "bar"), ("foo", "baz")))
            ]
        ],
        # Comma Separated Variant of Set-Cookie Headers
        [
            "foo=bar, doo=dar",
            [
                ("foo", "bar", ()),
                ("doo", "dar", ()),
            ]
        ],
        [
            "foo=bar; path=/, doo=dar; roo=rar; zoo=zar",
            [
                ("foo", "bar", (("path", "/"),)),
                ("doo", "dar", (("roo", "rar"), ("zoo", "zar"))),
            ]
        ],
        [
            "foo=bar; expires=Mon, 24 Aug 2037",
            [
                ("foo", "bar", (("expires", "Mon, 24 Aug 2037"),)),
            ]
        ],
        [
            "foo=bar; expires=Mon, 24 Aug 2037 00:00:00 GMT, doo=dar",
            [
                ("foo", "bar", (("expires", "Mon, 24 Aug 2037 00:00:00 GMT"),)),
                ("doo", "dar", ()),
            ]
        ],
    ]
    for s, expected in vals:
        ret = cookies.parse_set_cookie_header(s)
        if expected:
            for i in range(len(expected)):
                set_cookie_equal(ret[i], expected[i])

            s2 = cookies.format_set_cookie_header(ret)
            ret2 = cookies.parse_set_cookie_header(s2)
            for i in range(len(expected)):
                set_cookie_equal(ret2[i], expected[i])
        else:
            assert not ret


def test_refresh_cookie():

    # Invalid expires format, sent to us by Reddit.
    c = "rfoo=bar; Domain=reddit.com; expires=Thu, 31 Dec 2037 23:59:59 GMT; Path=/"
    assert cookies.refresh_set_cookie_header(c, 60)

    c = "MOO=BAR; Expires=Tue, 08-Mar-2011 00:20:38 GMT; Path=foo.com; Secure"
    assert "00:21:38" in cookies.refresh_set_cookie_header(c, 60)

    c = "foo,bar"
    with raises(ValueError):
        cookies.refresh_set_cookie_header(c, 60)

    # https://github.com/mitmproxy/mitmproxy/issues/773
    c = ">=A"
    assert cookies.refresh_set_cookie_header(c, 60)

    # https://github.com/mitmproxy/mitmproxy/issues/1118
    c = "foo:bar=bla"
    assert cookies.refresh_set_cookie_header(c, 0)
    c = "foo/bar=bla"
    assert cookies.refresh_set_cookie_header(c, 0)


@mock.patch('time.time')
def test_get_expiration_ts(*args):
    # Freeze time
    now_ts = 17
    time.time.return_value = now_ts

    CA = cookies.CookieAttrs
    F = cookies.get_expiration_ts

    assert F(CA([("Expires", "Thu, 01-Jan-1970 00:00:00 GMT")])) == 0
    assert F(CA([("Expires", "Mon, 24-Aug-2037 00:00:00 GMT")])) == 2134684800

    assert F(CA([("Max-Age", "0")])) == now_ts
    assert F(CA([("Max-Age", "31")])) == now_ts + 31


def test_is_expired():
    CA = cookies.CookieAttrs

    # A cookie can be expired
    # by setting the expire time in the past
    assert cookies.is_expired(CA([("Expires", "Thu, 01-Jan-1970 00:00:00 GMT")]))

    # or by setting Max-Age to 0
    assert cookies.is_expired(CA([("Max-Age", "0")]))

    # or both
    assert cookies.is_expired(CA([("Expires", "Thu, 01-Jan-1970 00:00:00 GMT"), ("Max-Age", "0")]))

    assert not cookies.is_expired(CA([("Expires", "Mon, 24-Aug-2037 00:00:00 GMT")]))
    assert not cookies.is_expired(CA([("Max-Age", "1")]))
    assert not cookies.is_expired(CA([("Expires", "Wed, 15-Jul-2037 00:00:00 GMT"), ("Max-Age", "1")]))

    assert not cookies.is_expired(CA([("Max-Age", "nan")]))
    assert not cookies.is_expired(CA([("Expires", "false")]))


def test_group_cookies():
    CA = cookies.CookieAttrs
    groups = [
        [
            "one=uno; foo=bar; foo=baz",
            [
                ('one', 'uno', CA([])),
                ('foo', 'bar', CA([])),
                ('foo', 'baz', CA([]))
            ]
        ],
        [
            "one=uno; Path=/; foo=bar; Max-Age=0; foo=baz; expires=24-08-1993",
            [
                ('one', 'uno', CA([('Path', '/')])),
                ('foo', 'bar', CA([('Max-Age', '0')])),
                ('foo', 'baz', CA([('expires', '24-08-1993')]))
            ]
        ],
        [
            "one=uno;",
            [
                ('one', 'uno', CA([]))
            ]
        ],
        [
            "one=uno; Path=/; Max-Age=0; Expires=24-08-1993",
            [
                ('one', 'uno', CA([('Path', '/'), ('Max-Age', '0'), ('Expires', '24-08-1993')]))
            ]
        ],
        [
            "path=val; Path=/",
            [
                ('path', 'val', CA([('Path', '/')]))
            ]
        ]
    ]

    for c, expected in groups:
        observed = cookies.group_cookies(cookies.parse_cookie_header(c))
        assert observed == expected
