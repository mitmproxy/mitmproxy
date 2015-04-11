from netlib import http_cookies, odict
import nose.tools


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
        nose.tools.eq_(http_cookies._read_token(*q), a)


def test_read_quoted_string():
    tokens = [
        [('"foo" x', 0), ("foo", 5)],
        [('"f\oo" x', 0), ("foo", 6)],
        [(r'"f\\o" x', 0), (r"f\o", 6)],
        [(r'"f\\" x', 0), (r"f" + '\\', 5)],
        [('"fo\\\"" x', 0), ("fo\"", 6)],
    ]
    for q, a in tokens:
        nose.tools.eq_(http_cookies._read_quoted_string(*q), a)


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
        ret, off = http_cookies._read_pairs(s)
        nose.tools.eq_(ret, lst)


def test_pairs_roundtrips():
    pairs = [
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
        ret, off = http_cookies._read_pairs(s)
        nose.tools.eq_(ret, lst)
        s2 = http_cookies._format_pairs(lst)
        ret, off = http_cookies._read_pairs(s2)
        nose.tools.eq_(ret, lst)


def test_parse_set_cookie():
    pass
