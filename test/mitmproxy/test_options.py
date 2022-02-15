from mitmproxy.options import get_config_dir, get_data_dir

from unittest import mock


DIRNAME = "dotdir"

HOME_DOTDIR = f"/.{DIRNAME}"
XDG_CONFIG_DIR = f"/.config/{DIRNAME}"
XDG_DATA_DIR = f"/.local/share/{DIRNAME}"


def is_home_dotdir(dirpath):
    return dirpath.endswith(HOME_DOTDIR)


def is_xdg_config_dir(dirpath):
    return dirpath.endswith(f"{XDG_CONFIG_DIR}")


def is_xdg_data_dir(dirpath):
    return dirpath.endswith(f"{XDG_DATA_DIR}")


def test_get_configdir_home():

    def patch_os_path_isdir(*args, **kwargs):
        return is_home_dotdir(args[0])

    with mock.patch("os.path.isdir") as os_path_isdir:
        os_path_isdir.side_effect = patch_os_path_isdir
        assert get_config_dir(DIRNAME) == f"~{HOME_DOTDIR}"


def test_get_configdir_xdg():
    def patch_os_path_isdir(*args, **kwargs):
        return is_xdg_config_dir(args[0])

    with mock.patch("os.path.isdir") as os_path_isdir:
        os_path_isdir.side_effect = patch_os_path_isdir
        assert get_config_dir(DIRNAME).endswith(XDG_CONFIG_DIR)


def test_xdg_configdir_handle_envvar(monkeypatch):
    configdir_env = "/foo/bar/baz"
    monkeypatch.setenv("XDG_DATA_HOME", configdir_env)

    def patch_os_path_isdir(*args, **kwargs):
        return args[0] == f"{configdir_env}/{DIRNAME}"

    with mock.patch("os.path.isdir") as os_path_isdir:
        os_path_isdir.side_effect = patch_os_path_isdir
        assert get_data_dir(DIRNAME) == f"{configdir_env}/{DIRNAME}"


def test_get_configdir_both():

    def patch_os_path_isdir(*args, **kwargs):
        return is_home_dotdir(args[0]) or is_xdg_config_dir(args[0])

    with mock.patch("os.path.isdir") as os_path_isdir:
        with mock.patch("logging.warning") as log:
            os_path_isdir.side_effect = patch_os_path_isdir
            assert get_config_dir(DIRNAME).endswith(XDG_CONFIG_DIR)
            log.assert_called()


def test_get_datadir_home():

    def patch_os_path_isdir(*args, **kwargs):
        return is_home_dotdir(args[0])

    with mock.patch("os.path.isdir") as os_path_isdir:
        os_path_isdir.side_effect = patch_os_path_isdir
        assert get_data_dir(DIRNAME) == f"~{HOME_DOTDIR}"


def test_get_datadir_xdg():

    def patch_os_path_isdir(*args, **kwargs):
        return is_xdg_data_dir(args[0])

    with mock.patch("os.path.isdir") as os_path_isdir:
        os_path_isdir.side_effect = patch_os_path_isdir
        assert get_data_dir(DIRNAME).endswith(XDG_DATA_DIR)


def test_xdg_datadir_handle_envvar(monkeypatch):
    datadir_env = "/foo/bar/baz"
    monkeypatch.setenv("XDG_DATA_HOME", datadir_env)

    def patch_os_path_isdir(*args, **kwargs):
        return args[0] == f"{datadir_env}/{DIRNAME}"

    with mock.patch("os.path.isdir") as os_path_isdir:
        os_path_isdir.side_effect = patch_os_path_isdir
        assert get_data_dir(DIRNAME) == f"{datadir_env}/{DIRNAME}"


def test_get_datadir_both():

    def patch_os_path_isdir(*args, **kwargs):
        return is_home_dotdir(args[0]) or is_xdg_data_dir(args[0])

    with mock.patch("os.path.isdir") as os_path_isdir:
        with mock.patch("logging.warning") as log:
            os_path_isdir.side_effect = patch_os_path_isdir
            assert get_data_dir(DIRNAME).endswith(XDG_DATA_DIR)
            log.assert_called()
