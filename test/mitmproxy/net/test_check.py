from mitmproxy.net import check


def test_is_valid_host():
    assert not check.is_valid_host(b"")
    assert not check.is_valid_host(b"xn--ke.ws")
    assert check.is_valid_host(b"one.two")
    assert not check.is_valid_host(b"one" * 255)
    assert check.is_valid_host(b"one.two.")
    # Allow underscore
    assert check.is_valid_host(b"one_two")
    assert check.is_valid_host(b"::1")

    # IP Address Validations
    assert check.is_valid_host(b'127.0.0.1')
    assert check.is_valid_host(b'2001:0db8:85a3:0000:0000:8a2e:0370:7334')
    assert check.is_valid_host(b'2001:db8:85a3:0:0:8a2e:370:7334')
    assert check.is_valid_host(b'2001:db8:85a3::8a2e:370:7334')
    assert not check.is_valid_host(b'2001:db8::85a3::7334')
    assert check.is_valid_host(b'2001-db8-85a3-8d3-1319-8a2e-370-7348.ipv6-literal.net')

    # TLD must be between 2 and 63 chars
    assert check.is_valid_host(b'example.tl')
    assert check.is_valid_host(b'example.tld')
    assert check.is_valid_host(b'example.' + b"x" * 63)
    assert not check.is_valid_host(b'example.' + b"x" * 64)

    # misc characters test
    assert not check.is_valid_host(b'ex@mple')
    assert not check.is_valid_host(b'ex@mple.com')
    assert not check.is_valid_host(b'example..com')
    assert not check.is_valid_host(b'.example.com')
    assert not check.is_valid_host(b'@.example.com')
    assert not check.is_valid_host(b'!.example.com')

    # Every label must be between 1 and 63 chars
    assert not check.is_valid_host(b'.tld')
    assert check.is_valid_host(b'x' * 1 + b'.tld')
    assert check.is_valid_host(b'x' * 30 + b'.tld')
    assert not check.is_valid_host(b'x' * 64 + b'.tld')
    assert check.is_valid_host(b'x' * 1 + b'.example.tld')
    assert check.is_valid_host(b'x' * 30 + b'.example.tld')
    assert not check.is_valid_host(b'x' * 64 + b'.example.tld')

    # Misc Underscore Test Cases
    assert check.is_valid_host(b'_example')
    assert check.is_valid_host(b'_example_')
    assert check.is_valid_host(b'example_')
    assert check.is_valid_host(b'_a.example.tld')
    assert check.is_valid_host(b'a_.example.tld')
    assert check.is_valid_host(b'_a_.example.tld')

    # Misc Dash/Hyphen/Minus Test Cases
    assert check.is_valid_host(b'-example')
    assert check.is_valid_host(b'-example_')
    assert check.is_valid_host(b'example-')
    assert check.is_valid_host(b'-a.example.tld')
    assert check.is_valid_host(b'a-.example.tld')
    assert check.is_valid_host(b'-a-.example.tld')

    # Misc Combo Test Cases
    assert check.is_valid_host(b'api-.example.com')
    assert check.is_valid_host(b'__a.example-site.com')
    assert check.is_valid_host(b'_-a.example-site.com')
    assert check.is_valid_host(b'_a_.example-site.com')
    assert check.is_valid_host(b'-a-.example-site.com')
    assert check.is_valid_host(b'api-.a.example.com')
    assert check.is_valid_host(b'api-._a.example.com')
    assert check.is_valid_host(b'api-.a_.example.com')
    assert check.is_valid_host(b'api-.ab.example.com')

    # Test str
    assert check.is_valid_host('example.tld')
    assert not check.is_valid_host("foo..bar")  # cannot be idna-encoded.