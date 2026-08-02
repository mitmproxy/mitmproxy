import json

from mitmproxy import http
from mitmproxy.test import tflow

BODY = json.dumps(
    {
        "users": [
            {"id": 1, "name": "alice", "token": "needle-one"},
            {"id": 2, "name": "bob", "token": "quiet"},
            {"id": 3, "name": "needle-two", "token": "xyz"},
        ],
        "total": 3,
    },
    indent=2,
).encode()


def _searchable(console):
    return console.window.focus_stack().top_widget().body._w.body


async def test_search_moves_between_matches(console):
    f = tflow.tflow(
        req=http.Request.make(
            "POST",
            "http://example.com",
            BODY,
            headers={"Content-Type": "application/json"},
        ),
    )
    await console.load_flow(f)
    console.type("<enter>")

    body = _searchable(console)
    assert len(body.body) > 5, "request body must be split into one widget per line"

    console.type("/needle<enter>")
    first = body.current_highlight
    assert first is not None

    console.type("n")
    second = body.current_highlight
    assert second is not None
    assert second != first, "'n' must jump to the next match"

    console.type("N")
    assert body.current_highlight == first, "'N' must jump back to the previous match"


async def test_search_survives_view_rebuild(console):
    f = tflow.tflow(
        req=http.Request.make(
            "POST",
            "http://example.com",
            BODY,
            headers={"Content-Type": "application/json"},
        ),
    )
    await console.load_flow(f)
    console.type("<enter>")
    console.type("/needle<enter>")

    # A flow update rebuilds the whole flow view; the search term must survive it.
    console.window.focus_changed()
    console.type("n")

    body = _searchable(console)
    assert body.current_highlight is not None, (
        "'n' must still work after the view was rebuilt"
    )


async def test_search_keeps_syntax_highlighting(console):
    f = tflow.tflow(
        req=http.Request.make(
            "POST",
            "http://example.com",
            BODY,
            headers={"Content-Type": "application/json"},
        ),
    )
    await console.load_flow(f)
    console.type("<enter>")
    console.type("/needle<enter>")

    body = _searchable(console)
    highlighted = body.body[body.current_highlight]

    attrs = set()
    for row in highlighted.render((80,)).content():
        for attr, _, _text in row:
            attrs.add(attr)

    assert "focusfield" in attrs, "the match itself must be emphasized"
    assert attrs - {"focusfield", None}, (
        "syntax highlighting must survive on the rest of the line"
    )
