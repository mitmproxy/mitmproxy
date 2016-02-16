import mitmproxy.contentviews as cv
from netlib.http import Headers


def test_custom_views():
    class ViewNoop(cv.View):
        name = "noop"
        prompt = ("noop", "n")
        content_types = ["text/none"]

        def __call__(self, data, **metadata):
            return "noop", cv.format_text(data)

    view_obj = ViewNoop()

    cv.add(view_obj)

    assert cv.get("noop")

    r = cv.get_content_view(
        cv.get("noop"),
        "[1, 2, 3]",
        headers=Headers(
            content_type="text/plain"
        )
    )
    assert "noop" in r[0]

    # now try content-type matching
    r = cv.get_content_view(
        cv.get("Auto"),
        "[1, 2, 3]",
        headers=Headers(
            content_type="text/none"
        )
    )
    assert "noop" in r[0]

    # now try removing the custom view
    cv.remove(view_obj)
    r = cv.get_content_view(
        cv.get("Auto"),
        "[1, 2, 3]",
        headers=Headers(
            content_type="text/none"
        )
    )
    assert "noop" not in r[0]
