# Default view cutoff *in lines*
import typing

KEY_MAX = 30

TTextType = typing.Union[str, bytes]  # FIXME: This should be either bytes or str ultimately.
TViewLine = typing.List[typing.Tuple[str, TTextType]]
TViewResult = typing.Tuple[str, typing.Iterator[TViewLine]]


class View:
    name: typing.ClassVar[str]
    content_types: typing.ClassVar[typing.List[str]] = []

    def __call__(self, data: bytes, **metadata) -> TViewResult:
        """
        Transform raw data into human-readable output.

        Args:
            data: the data to decode/format.
            metadata: optional keyword-only arguments for metadata. Implementations must not
                rely on a given argument being present.

        Returns:
            A (description, content generator) tuple.

            The content generator yields lists of (style, text) tuples, where each list represents
            a single line. ``text`` is a unfiltered byte string which may need to be escaped,
            depending on the used output.

        Caveats:
            The content generator must not yield tuples of tuples,
            because urwid cannot process that. You have to yield a *list* of tuples per line.
        """
        raise NotImplementedError()  # pragma: no cover


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
