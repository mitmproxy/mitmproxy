import pytest

from mitmproxy.contentviews import css
from mitmproxy.test import tutils
from . import full_eval

data = tutils.test_data.push("mitmproxy/contentviews/test_css_data/")


@pytest.mark.parametrize("filename", [
    "animation-keyframe.css",
    "blank-lines-and-spaces.css",
    "block-comment.css",
    "empty-rule.css",
    "import-directive.css",
    "indentation.css",
    "media-directive.css",
    "quoted-string.css",
    "selectors.css",
    "simple.css",
])
def test_beautify(filename):
    path = data.path(filename)
    with open(path) as f:
        input = f.read()
    with open("-formatted.".join(path.rsplit(".", 1))) as f:
        expected = f.read()
    formatted = css.beautify(input)
    assert formatted == expected


def test_simple():
    v = full_eval(css.ViewCSS())
    assert v(b"#foo{color:red}") == ('CSS', [
        [('text', '#foo {')],
        [('text', '    color: red')],
        [('text', '}')]
    ])
    assert v(b"") == ('CSS', [[('text', '')]])
    assert v(b"console.log('not really css')") == (
        'CSS', [[('text', "console.log('not really css')")]]
    )
