from libmproxy import script, flow
import libmproxy.contentviews as cv
from netlib.http import Headers


def test_custom_views():
    plugins = flow.Plugins()

    # two types: view and action
    assert 'view_plugins' in dict(plugins).keys()

    view_plugins = plugins['view_plugins']
    assert len(view_plugins) == 0

    class ViewNoop(cv.View):
        name = "noop"
        prompt = ("noop", "n")
        content_types = ["text/none"]

        def __call__(self, data, **metadata):
            return "noop", cv.format_text(data)

    plugins.register_view('noop',
                          title='Noop View Plugin',
                          class_ref=ViewNoop)

    assert len(view_plugins) == 1
    assert view_plugins['noop']['title'] == 'Noop View Plugin'

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
