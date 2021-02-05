# Default view cutoff *in lines*
import typing
from abc import ABC, abstractmethod

from mitmproxy import flow
from mitmproxy import http

KEY_MAX = 30

TTextType = typing.Union[str, bytes]  # FIXME: This should be either bytes or str ultimately.
TViewLine = typing.List[typing.Tuple[str, TTextType]]
TViewResult = typing.Tuple[str, typing.Iterator[TViewLine]]


class View(ABC):
    name: typing.ClassVar[str]

    @abstractmethod
    def __call__(
        self,
        data: bytes,
        *,
        content_type: typing.Optional[str] = None,
        flow: typing.Optional[flow.Flow] = None,
        http_message: typing.Optional[http.Message] = None,
        **unknown_metadata,
    ) -> TViewResult:
        """
        Transform raw data into human-readable output.

        Returns a (description, content generator) tuple.
        The content generator yields lists of (style, text) tuples, where each list represents
        a single line. ``text`` is a unfiltered string which may need to be escaped,
        depending on the used output. For example, it may contain terminal control sequences
        or unfiltered HTML.

        Except for `data`, implementations must not rely on any given argument to be present.
        To ensure compatibility with future mitmproxy versions, unknown keyword arguments should be ignored.

        The content generator must not yield tuples of tuples, because urwid cannot process that.
        You have to yield a *list* of tuples per line.
        """
        raise NotImplementedError()  # pragma: no cover

    def render_priority(
        self,
        data: bytes,
        *,
        content_type: typing.Optional[str] = None,
        flow: typing.Optional[flow.Flow] = None,
        http_message: typing.Optional[http.Message] = None,
        **unknown_metadata,
    ) -> float:
        """
        Return the priority of this view for rendering `data`.
        If no particular view is chosen by the user, the view with the highest priority is selected.

        Except for `data`, implementations must not rely on any given argument to be present.
        To ensure compatibility with future mitmproxy versions, unknown keyword arguments should be ignored.
        """
        return 0

    def __lt__(self, other):
        assert isinstance(other, View)
        return self.name.__lt__(other.name)


def format_pairs(
    items: typing.Iterable[typing.Tuple[TTextType, TTextType]]
) -> typing.Iterator[TViewLine]:
    """
    Helper function that accepts a list of (k,v) pairs into a list of
    [
        ("key", key    )
        ("value", value)
    ]
    where key is padded to a uniform width
    """

    max_key_len = max((len(k[0]) for k in items), default=0)
    max_key_len = min((max_key_len, KEY_MAX), default=0)

    for key, value in items:
        if isinstance(key, bytes):

            key += b":"
        else:
            key += ":"

        key = key.ljust(max_key_len + 2)

        yield [
            ("header", key),
            ("text", value)
        ]


def format_dict(
    d: typing.Mapping[TTextType, TTextType]
) -> typing.Iterator[TViewLine]:
    """
    Helper function that transforms the given dictionary into a list of
    [
        ("key",   key  )
        ("value", value)
    ]
    entries, where key is padded to a uniform width.
    """

    return format_pairs(d.items())


def format_text(text: TTextType) -> typing.Iterator[TViewLine]:
    """
    Helper function that transforms bytes into the view output format.
    """
    for line in text.splitlines():
        yield [("text", line)]
