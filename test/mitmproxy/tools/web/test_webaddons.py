import pytest

from mitmproxy.exceptions import OptionsError
from mitmproxy.test import taddons
from mitmproxy.tools.web import webaddons


class TestWebAuth:
    def test_token_auth(self):
        a = webaddons.WebAuth()
        with taddons.context(webaddons.WebAddon(), a) as tctx:
            assert not a.is_valid_password("")
            assert not a.is_valid_password("invalid")
            assert not a.is_valid_password("test")

            tctx.options.web_password = ""
            assert not a.is_valid_password("")
            assert not a.is_valid_password("invalid")
            assert not a.is_valid_password("test")
            assert a.is_valid_password(a._password)
            assert "token" in a.web_url

    def test_plaintext_auth(self, caplog):
        a = webaddons.WebAuth()
        with taddons.context(webaddons.WebAddon(), a) as tctx:
            tctx.options.web_password = "test"
            assert "Consider using an argon2 hash" in caplog.text
            assert not a.is_valid_password("")
            assert not a.is_valid_password("invalid")
            assert a.is_valid_password("test")
            assert "token" not in a.web_url

    def test_argon2_auth(self, caplog):
        a = webaddons.WebAuth()
        with taddons.context(webaddons.WebAddon(), a) as tctx:
            tctx.options.web_password = (
                "$argon2id$v=19$m=8,t=1,p=1$c2FsdHNhbHQ$ieVgG5ysTJFx4k/KvmC9aQ"
            )
            assert not a.is_valid_password("")
            assert not a.is_valid_password("invalid")
            assert a.is_valid_password("test")
            assert "token" not in a.web_url

    def test_invalid_hash(self, caplog):
        a = webaddons.WebAuth()
        with taddons.context(webaddons.WebAddon(), a) as tctx:
            with pytest.raises(OptionsError):
                tctx.options.web_password = "$argon2id$"
            assert not a.is_valid_password("")
            assert not a.is_valid_password("test")
