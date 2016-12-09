from mitmproxy.utils import sliding_window


def test_simple():
    y = list(sliding_window.window(range(1000, 1005), 1, 2))
    assert y == [
        # prev this  next  next2
        (None, 1000, 1001, 1002),
        (1000, 1001, 1002, 1003),
        (1001, 1002, 1003, 1004),
        (1002, 1003, 1004, None),
        (1003, 1004, None, None)
    ]


def test_is_lazy():
    done = False

    def gen():
        nonlocal done
        done = True
        yield 42

    x = sliding_window.window(gen(), 1, 1)
    assert not done
    assert list(x)
    assert done
