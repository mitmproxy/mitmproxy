from mitmproxy.test import tflow

_NOT_IMPORTANT_LINE = "not important"
_ABOVE_FIRST_SEARCHED_TEXT = "above first searched text"
_ABOVE_SECOND_SEARCHED_TEXT = "above second searched text"
_ABOVE_THIRD_SEARCHED_TEXT = "above third searched text"
_SEARCHED_TEXT = "searched_text"

def _line(content):
    return f"{content}\r\n"

assert _SEARCHED_TEXT not in _NOT_IMPORTANT_LINE
assert _SEARCHED_TEXT not in _ABOVE_FIRST_SEARCHED_TEXT
assert _SEARCHED_TEXT not in _ABOVE_SECOND_SEARCHED_TEXT
assert _SEARCHED_TEXT not in _ABOVE_THIRD_SEARCHED_TEXT
assert _ABOVE_FIRST_SEARCHED_TEXT != _ABOVE_SECOND_SEARCHED_TEXT
assert _ABOVE_FIRST_SEARCHED_TEXT != _ABOVE_THIRD_SEARCHED_TEXT
assert _ABOVE_SECOND_SEARCHED_TEXT != _ABOVE_THIRD_SEARCHED_TEXT

_TEST_CONSOLE_HEIGHT = 24
_NUMBER_OF_LINES_LOADED_IN_TRUNCATED_MODE = 512

async def test_flowview(monkeypatch, console):
    for f in tflow.tflows():
        console.commands.call("view.clear")
        await console.load_flow(f)
        console.type("<enter><tab><tab>")


async def test_flowview_searched_data_truncated_user_offered_to_load_data(console):
    assert "Flows" in console.screen_contents()
    flow = tflow.tflow()

    flow.request.headers["content-type"] = "text/plain"
    flow.request.raw_content = \
        (_line(_NOT_IMPORTANT_LINE) * 4) + \
        _line(_ABOVE_FIRST_SEARCHED_TEXT) + \
        _line(_SEARCHED_TEXT) + \
        (_line(_NOT_IMPORTANT_LINE) * (_TEST_CONSOLE_HEIGHT*2)) + \
        _line(_ABOVE_SECOND_SEARCHED_TEXT) + \
        _line(_SEARCHED_TEXT) + \
        (_line(_NOT_IMPORTANT_LINE) * _NUMBER_OF_LINES_LOADED_IN_TRUNCATED_MODE) + \
        _line(_ABOVE_THIRD_SEARCHED_TEXT) + \
        _line(_SEARCHED_TEXT) + \
        (_line(_NOT_IMPORTANT_LINE) * _NUMBER_OF_LINES_LOADED_IN_TRUNCATED_MODE)

    await console.load_flow(flow)

    assert ">>" in console.screen_contents()

    console.type("<enter>")

    assert "Flow Details" in console.screen_contents()

    console.type("/searched_text<enter>")

    assert _ABOVE_FIRST_SEARCHED_TEXT in console.screen_contents()
    assert _ABOVE_SECOND_SEARCHED_TEXT not in console.screen_contents()
    assert _ABOVE_THIRD_SEARCHED_TEXT not in console.screen_contents()

    console.type("n")

    assert _ABOVE_FIRST_SEARCHED_TEXT not in console.screen_contents()
    assert _ABOVE_SECOND_SEARCHED_TEXT in console.screen_contents()
    assert _ABOVE_THIRD_SEARCHED_TEXT not in console.screen_contents()

    console.type("n")

    assert "Searched text found in truncated content, load full contents?" \
           in console.screen_contents()

    console.type("y")

    assert _ABOVE_FIRST_SEARCHED_TEXT not in console.screen_contents()
    assert _ABOVE_SECOND_SEARCHED_TEXT not in console.screen_contents()
    assert _ABOVE_THIRD_SEARCHED_TEXT in console.screen_contents()

    console.type("n")

    assert _ABOVE_FIRST_SEARCHED_TEXT in console.screen_contents()
    assert _ABOVE_SECOND_SEARCHED_TEXT not in console.screen_contents()
    assert _ABOVE_THIRD_SEARCHED_TEXT not in console.screen_contents()

async def test_flowview_no_searched_data_truncated_user_not_offered_to_load_data(console):
    assert "Flows" in console.screen_contents()
    flow = tflow.tflow()

    flow.request.headers["content-type"] = "text/plain"
    flow.request.raw_content = \
        (_line(_NOT_IMPORTANT_LINE) * 4) + \
        _line(_ABOVE_FIRST_SEARCHED_TEXT) + \
        _line(_SEARCHED_TEXT) + \
        (_line(_NOT_IMPORTANT_LINE) * (_TEST_CONSOLE_HEIGHT*2)) + \
        _line(_ABOVE_SECOND_SEARCHED_TEXT) + \
        _line(_SEARCHED_TEXT) + \
        (_line(_NOT_IMPORTANT_LINE) * _NUMBER_OF_LINES_LOADED_IN_TRUNCATED_MODE) + \
        _line("not_the_text_you_looking_for") + \
        (_line(_NOT_IMPORTANT_LINE) * _NUMBER_OF_LINES_LOADED_IN_TRUNCATED_MODE)

    await console.load_flow(flow)

    assert ">>" in console.screen_contents()

    console.type("<enter>")

    assert "Flow Details" in console.screen_contents()

    console.type("/searched_text<enter>")

    assert _ABOVE_FIRST_SEARCHED_TEXT in console.screen_contents()
    assert _ABOVE_SECOND_SEARCHED_TEXT not in console.screen_contents()

    console.type("n")

    assert _ABOVE_FIRST_SEARCHED_TEXT not in console.screen_contents()
    assert _ABOVE_SECOND_SEARCHED_TEXT in console.screen_contents()

    console.type("n")

    assert "Searched text found in truncated content, load full contents?" \
           not in console.screen_contents()

    assert _ABOVE_FIRST_SEARCHED_TEXT in console.screen_contents()
    assert _ABOVE_SECOND_SEARCHED_TEXT not in console.screen_contents()


async def test_flowview_searched_backwards_data_truncated_user_offered_to_load_data(console):
    assert "Flows" in console.screen_contents()
    flow = tflow.tflow()

    flow.request.headers["content-type"] = "text/plain"
    flow.request.raw_content = \
        (_line(_NOT_IMPORTANT_LINE) * 4) + \
        _line(_ABOVE_FIRST_SEARCHED_TEXT) + \
        _line(_SEARCHED_TEXT) + \
        (_line(_NOT_IMPORTANT_LINE) * (_NUMBER_OF_LINES_LOADED_IN_TRUNCATED_MODE * 2)) + \
        _line(_ABOVE_SECOND_SEARCHED_TEXT) + \
        _line(_SEARCHED_TEXT) + \
        (_line(_NOT_IMPORTANT_LINE) * _NUMBER_OF_LINES_LOADED_IN_TRUNCATED_MODE)

    await console.load_flow(flow)

    assert ">>" in console.screen_contents()

    console.type("<enter>")

    assert "Flow Details" in console.screen_contents()

    console.type("/searched_text<enter>")

    assert _ABOVE_FIRST_SEARCHED_TEXT in console.screen_contents()
    assert _ABOVE_SECOND_SEARCHED_TEXT not in console.screen_contents()

    console.type("N")

    assert "Searched text found in truncated content, load full contents?" \
           in console.screen_contents()

    console.type("y")

    assert _ABOVE_FIRST_SEARCHED_TEXT not in console.screen_contents()
    assert _ABOVE_SECOND_SEARCHED_TEXT in console.screen_contents()
