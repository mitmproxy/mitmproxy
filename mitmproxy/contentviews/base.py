import traceback
from typing import AnyStr
from typing import Iterable
from typing import List
from typing import Mapping
from typing import Optional
from typing import Tuple

from mitmproxy import exceptions
from mitmproxy.net import http
from mitmproxy.utils import strutils


VIEW_CUTOFF = 512
KEY_MAX = 30

views = []  # type: List[View]
content_types_map = {}  # type: Dict[str, List[View]]
view_prompts = []  # type: List[Tuple[str, str]]


class View:
    name = None  # type: str
    prompt = None  # type: Tuple[str,str]
    content_types = []  # type: List[str]

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
        raise NotImplementedError()  # pragma: no cover


def format_dict(
        d: Mapping[AnyStr, AnyStr]
) -> Iterable[List[Tuple[str, AnyStr]]]:
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


def format_text(text: AnyStr) -> Iterable[List[Tuple[str, AnyStr]]]:
    """
    Helper function that transforms bytes into the view output format.
    """
    for line in text.splitlines():
        yield [("text", line)]


def get(name: str) -> Optional[View]:
    for i in views:
        if i.name.lower() == name.lower():
            return i


def get_by_shortcut(c: str) -> Optional[View]:
    for i in views:
        if i.prompt[1] == c:
            return i


def add(view: View) -> None:
    # TODO: auto-select a different name (append an integer?)
    for i in views:
        if i.name == view.name:
            raise exceptions.ContentViewException("Duplicate view: " + view.name)

    # TODO: the UI should auto-prompt for a replacement shortcut
    for prompt in view_prompts:
        if prompt[1] == view.prompt[1]:
            raise exceptions.ContentViewException("Duplicate view shortcut: " + view.prompt[1])

    views.append(view)

    for ct in view.content_types:
        l = content_types_map.setdefault(ct, [])
        l.append(view)

    view_prompts.append(view.prompt)


def remove(view: View) -> None:
    for ct in view.content_types:
        l = content_types_map.setdefault(ct, [])
        l.remove(view)

        if not len(l):
            del content_types_map[ct]

    view_prompts.remove(view.prompt)
    views.remove(view)


def safe_to_print(lines, encoding="utf8"):
    """
    Wraps a content generator so that each text portion is a *safe to print* unicode string.
    """
    for line in lines:
        clean_line = []
        for (style, text) in line:
            if isinstance(text, bytes):
                text = text.decode(encoding, "replace")
            text = strutils.escape_control_characters(text)
            clean_line.append((style, text))
        yield clean_line


def get_message_content_view(viewname, message):
    """
    Like get_content_view, but also handles message encoding.
    """
    viewmode = get(viewname)
    if not viewmode:
        viewmode = get("auto")
    try:
        content = message.content
    except ValueError:
        content = message.raw_content
        enc = "[cannot decode]"
    else:
        if isinstance(message, http.Message) and content != message.raw_content:
            enc = "[decoded {}]".format(
                message.headers.get("content-encoding")
            )
        else:
            enc = None

    if content is None:
        return "", iter([[("error", "content missing")]]), None

    metadata = {}
    if isinstance(message, http.Request):
        metadata["query"] = message.query
    if isinstance(message, http.Message):
        metadata["headers"] = message.headers

    description, lines, error = get_content_view(
        viewmode, content, **metadata
    )

    if enc:
        description = "{} {}".format(enc, description)

    return description, lines, error


def get_content_view(viewmode: View, data: bytes, **metadata):
    """
        Args:
            viewmode: the view to use.
            data,
            **metadata: arguments passed to View instance.

        Returns:
            A (description, content generator, error) tuple.
            If the content view raised an exception generating the view,
            the exception is returned in error and the flow is formatted in raw mode.
            In contrast to calling the views directly, text is always safe-to-print unicode.
    """
    try:
        ret = viewmode(data, **metadata)
        if ret is None:
            ret = "Couldn't parse: falling back to Raw", get("Raw")(data, **metadata)[1]
        desc, content = ret
        error = None
    # Third-party viewers can fail in unexpected ways...
    except Exception:
        desc = "Couldn't parse: falling back to Raw"
        _, content = get("Raw")(data, **metadata)
        error = "{} Content viewer failed: \n{}".format(
            getattr(viewmode, "name"),
            traceback.format_exc()
        )

    return desc, safe_to_print(content), error
