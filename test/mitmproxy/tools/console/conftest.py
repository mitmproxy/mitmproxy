from unittest import mock

import pytest


@pytest.fixture(scope="module", autouse=True)
def definitely_atty():
    with mock.patch("sys.stdout.isatty", lambda: True):
        yield
