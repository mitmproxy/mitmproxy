from mitmproxy.utils import emoji
from mitmproxy.tools.console.common import SYMBOL_MARK


def test_emoji():
    assert emoji.emoji[":default:"] == SYMBOL_MARK
