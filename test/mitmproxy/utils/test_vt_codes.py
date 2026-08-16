import io

from mitmproxy.utils.vt_codes import ensure_supported


def test_simple():
    assert not ensure_supported(io.StringIO())


def test_override_always():
    """`override="always"` returns True even for non-TTY file objects."""
    assert ensure_supported(io.StringIO(), override="always") is True


def test_override_never():
    """`override="never"` returns False even when isatty() reports True."""

    class FakeTTY:
        def isatty(self) -> bool:
            return True

    assert ensure_supported(FakeTTY(), override="never") is False


def test_override_auto_default():
    """`override="auto"` keeps the historical isatty()-based behavior."""
    # Default (no override) — equivalent to "auto".
    assert not ensure_supported(io.StringIO())
    assert not ensure_supported(io.StringIO(), override="auto")
