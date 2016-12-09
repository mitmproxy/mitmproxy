# Default view cutoff *in lines*

from typing import Iterable
from typing import Mapping
from typing import Tuple
from typing import Union

VIEW_CUTOFF = 512

KEY_MAX = 30


class View:
    name = None
    prompt = ()
    content_types = []

    def __call__(self, data: bytes, **metadata):
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
        raise NotImplementedError()


def format_dict(
        d: Mapping[Union[str, bytes], Union[str, bytes]]
) -> Iterable[Tuple[Union[str, bytes], Union[str, bytes]]]:
    """
    Helper function that transforms the given dictionary into a list of
        ("key",   key  )
        ("value", value)
    tuples, where key is padded to a uniform width.
    """
    max_key_len = max(len(k) for k in d.keys())
    max_key_len = min(max_key_len, KEY_MAX)
    for key, value in d.items():
        key += b":" if isinstance(key, bytes) else u":"
        key = key.ljust(max_key_len + 2)
        yield [
            ("header", key),
            ("text", value)
        ]


def format_text(text):
    """
    Helper function that transforms bytes into the view output format.
    """
    for line in text.splitlines():
        yield [("text", line)]
