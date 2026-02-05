import subprocess
from unittest import mock

import pytest

from mitmproxy import version
from mitmproxy.tools.console import versioninfo


class TestVersionInfo:
    @pytest.fixture
    def master(self):
        return mock.MagicMock()

    def test_init(self, master):
        vi = versioninfo.VersionInfo(master)
        assert vi.master == master
        assert vi.title == "Version Info"
        assert vi.keyctx == "versioninfo"

    def test_get_content_structure(self, master):
        vi = versioninfo.VersionInfo(master)
        content = vi._get_content()

        assert content is not None
        assert len(content) > 0

    def test_content_contains_version(self, master):
        vi = versioninfo.VersionInfo(master)
        content = vi._get_content()

        text_content = []
        for item in content:
            if hasattr(item, 'text'):
                if isinstance(item.text, list):
                    text_content.extend([str(t) for t in item.text])
                else:
                    text_content.append(str(item.text))

        assert any(version.VERSION in str(t) for t in text_content)

    def test_get_git_info_in_git_repo(self, master):
        vi = versioninfo.VersionInfo(master)
        git_info = vi._get_git_info()

        if git_info:
            assert isinstance(git_info, dict)
            assert "Commit Hash" in git_info
            assert "Full Commit Hash" in git_info
            assert len(git_info["Commit Hash"]) == 7
            assert len(git_info["Full Commit Hash"]) == 40

    def test_get_git_info_not_in_git_repo(self, master, monkeypatch):
        vi = versioninfo.VersionInfo(master)

        def mock_run(*args, **kwargs):
            raise subprocess.CalledProcessError(1, "git")

        monkeypatch.setattr(subprocess, "run", mock_run)

        git_info = vi._get_git_info()
        assert git_info is None

    def test_get_git_info_handles_missing_tag(self, master, monkeypatch):
        vi = versioninfo.VersionInfo(master)

        call_count = [0]

        def mock_check_output(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return b"abc123def456abc123def456abc123def456abc1\n"
            elif call_count[0] == 2:
                return b"2024-01-01 12:00:00 +0000\n"
            elif call_count[0] == 3:
                raise subprocess.CalledProcessError(128, "git")
            elif call_count[0] == 4:
                return b"main\n"
            return b""

        def mock_run(*args, **kwargs):
            pass

        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(subprocess, "check_output", mock_check_output)

        git_info = vi._get_git_info()

        assert git_info is not None
        assert "Commit Hash" in git_info
        assert "Last Tag" not in git_info

    def test_keypress_m_start(self, master):
        vi = versioninfo.VersionInfo(master)

        result = vi.keypress((80, 24), "m_start")
        assert result is None
        assert vi.focus_position == 0

    def test_keypress_m_end(self, master):
        vi = versioninfo.VersionInfo(master)

        result = vi.keypress((80, 24), "m_end")
        assert result is None
        assert vi.focus_position == len(vi.body) - 1

    def test_keypress_other_keys(self, master):
        vi = versioninfo.VersionInfo(master)

        vi.keypress((80, 24), "j")
        vi.keypress((80, 24), "down")

    def test_content_has_padding(self, master):
        vi = versioninfo.VersionInfo(master)
        content = vi._get_content()

        assert len(content) >= 5

    def test_git_info_with_branch(self, master, monkeypatch):
        vi = versioninfo.VersionInfo(master)

        call_count = [0]

        def mock_check_output(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return b"abc123def456abc123def456abc123def456abc1\n"
            elif call_count[0] == 2:
                return b"2024-01-01 12:00:00 +0000\n"
            elif call_count[0] == 3:
                return b"v1.0.0\n"
            elif call_count[0] == 4:
                return b"feature-branch\n"
            return b""

        def mock_run(*args, **kwargs):
            pass

        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(subprocess, "check_output", mock_check_output)

        git_info = vi._get_git_info()

        assert git_info is not None
        assert "Branch" in git_info
        assert git_info["Branch"] == "feature-branch"

    def test_version_get_dev_version_displayed(self, master):
        vi = versioninfo.VersionInfo(master)
        content = vi._get_content()

        text_content = []
        for item in content:
            if hasattr(item, 'text'):
                if isinstance(item.text, list):
                    text_content.extend([str(t) for t in item.text])
                else:
                    text_content.append(str(item.text))

        all_text = " ".join(text_content)
        assert version.VERSION in all_text

    def test_get_git_info_generic_exception(self, master, monkeypatch):
        vi = versioninfo.VersionInfo(master)

        def mock_run(*args, **kwargs):
            raise OSError("Permission denied")

        monkeypatch.setattr(subprocess, "run", mock_run)

        git_info = vi._get_git_info()
        assert git_info is None

    def test_get_git_info_missing_branch(self, master, monkeypatch):
        vi = versioninfo.VersionInfo(master)

        call_count = [0]

        def mock_check_output(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return b"abc123def456abc123def456abc123def456abc1\n"
            elif call_count[0] == 2:
                return b"2024-01-01 12:00:00 +0000\n"
            elif call_count[0] == 3:
                return b"v1.0.0\n"
            elif call_count[0] == 4:
                raise subprocess.CalledProcessError(128, "git")
            return b""

        def mock_run(*args, **kwargs):
            pass

        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(subprocess, "check_output", mock_check_output)

        git_info = vi._get_git_info()

        assert git_info is not None
        assert "Commit Hash" in git_info
        assert "Branch" not in git_info

    def test_content_displays_not_available_when_no_git(self, master, monkeypatch):
        def mock_get_git_info(self):
            return None

        monkeypatch.setattr(versioninfo.VersionInfo, "_get_git_info", mock_get_git_info)

        vi = versioninfo.VersionInfo(master)
        content = vi._get_content()

        text_content = []
        for item in content:
            if hasattr(item, 'text'):
                if isinstance(item.text, list):
                    text_content.extend([str(t) for t in item.text])
                else:
                    text_content.append(str(item.text))

        all_text = " ".join(text_content)
        assert "Not available" in all_text
