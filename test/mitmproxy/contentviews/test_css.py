from mitmproxy.contentviews import css
from mitmproxy.test import tutils
from . import full_eval

try:
    import cssutils
except:
    cssutils = None


def test_view_css():
    v = full_eval(css.ViewCSS())

    with open(tutils.test_data.path('mitmproxy/data/1.css'), 'r') as fp:
        fixture_1 = fp.read()

    result = v('a')

    if cssutils:
        assert len(list(result[1])) == 0
    else:
        assert len(list(result[1])) == 1

    result = v(fixture_1)

    if cssutils:
        assert len(list(result[1])) > 1
    else:
        assert len(list(result[1])) == 1
