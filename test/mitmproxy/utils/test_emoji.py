from mitmproxy.tools.console.common import SYMBOL_MARK
from mitmproxy.utils import emoji


def test_emoji():
    assert emoji.emoji[":default:"] == SYMBOL_MARK
