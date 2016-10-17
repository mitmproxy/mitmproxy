import io
import mock
from netlib import version_check


@mock.patch("sys.exit")
def test_check_pyopenssl_version(sexit):
    fp = io.StringIO()
    version_check.check_pyopenssl_version(fp=fp)
    assert not fp.getvalue()
    assert not sexit.called

    version_check.check_pyopenssl_version((9999,), fp=fp)
    assert "outdated" in fp.getvalue()
    assert sexit.called


@mock.patch("sys.exit")
@mock.patch("OpenSSL.__version__")
def test_unparseable_pyopenssl_version(version, sexit):
    version.split.return_value = ["foo", "bar"]
    fp = io.StringIO()
    version_check.check_pyopenssl_version(fp=fp)
    assert "Cannot parse" in fp.getvalue()
    assert not sexit.called
