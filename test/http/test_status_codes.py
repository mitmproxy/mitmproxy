from netlib.http import status_codes


def test_simple():
    assert status_codes.IM_A_TEAPOT == 418
    assert status_codes.RESPONSES[418] == "I'm a teapot"
