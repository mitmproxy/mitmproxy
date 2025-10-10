from pathlib import Path

import pytest

from mitmproxy.utils import htpasswd


def test_sha1():
    ht = htpasswd.HtpasswdFile(
        "user1:{SHA}8FePHnF0saQcTqjG4X96ijuIySo=\n"
        "user2:{SHA}i+UhJqb95FCnFio2UdWJu1HpV50=\n"
        "user3:{SHA}3ipNV1GrBtxPmHFC21fCbVCSXIo=:extra\n"
    )
    assert ht.check_password("user1", "pass1")
    assert ht.check_password("user2", "pass2")
    assert ht.check_password("user3", "pass3")
    assert not ht.check_password("user1", "pass2")
    assert not ht.check_password("wronguser", "testpassword")


def test_bcrypt():
    ht = htpasswd.HtpasswdFile(
        "user_bcrypt:$2b$05$opH8g9/PUhK6HVSnhdX7P.oB6MTMOlIlXgb4THm1Adh12t4IuqMsK\n"
    )
    assert ht.check_password("user_bcrypt", "pass")
    assert not ht.check_password("user_bcrypt", "wrong")


@pytest.mark.parametrize(
    "file_content, err_msg",
    [
        ("malformed", "Malformed htpasswd line"),
        (":malformed", "Malformed htpasswd line"),
        ("user_md5:$apr1$....", "Unsupported htpasswd format"),
        ("user_ssha:{SSHA}...", "Unsupported htpasswd format"),
        ("user_plain:pass", "Unsupported htpasswd format"),
        ("user_crypt:..j8N8I28nVM", "Unsupported htpasswd format"),
        ("user_empty_pw:", "Unsupported htpasswd format"),
    ],
)
def test_errors(file_content, err_msg):
    with pytest.raises(ValueError, match=err_msg):
        htpasswd.HtpasswdFile(file_content)


def test_from_file(tdata):
    assert htpasswd.HtpasswdFile.from_file(
        Path(tdata.path("mitmproxy/data/htpasswd"))
    ).users


def test_file_not_found():
    with pytest.raises(OSError, match="Htpasswd file not found"):
        htpasswd.HtpasswdFile.from_file(Path("/nonexistent"))


def test_empty_and_comments():
    ht = htpasswd.HtpasswdFile("\n# comment\n \n\t# another comment\n")
    assert not ht.users
