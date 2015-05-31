import cStringIO
import mock
from netlib import version_check, version


@mock.patch("sys.exit")
def test_version_check(sexit):
    fp = cStringIO.StringIO()
    version_check.version_check(version.IVERSION, fp=fp)
    assert not sexit.called

    b = (version.IVERSION[0] - 1, version.IVERSION[1])
    version_check.version_check(b, fp=fp)
    assert sexit.called

    sexit.reset_mock()
    version_check.version_check(
        version.IVERSION,
        pyopenssl_min_version=(9999,),
        fp=fp
    )
    assert sexit.called
