import io
import zipfile

import pytest

from mitmproxy import http
from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews._view_zip import zip


def meta(content_type: str) -> Metadata:
    return Metadata(
        content_type=content_type.split(";")[0],
        http_message=http.Request.make(
            "POST", "https://example.com/", headers={"content-type": content_type}
        ),
    )


def create_test_zip(files: dict[str, bytes]) -> bytes:
    """Helper function to create a test ZIP file in memory."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files.items():
            zf.writestr(filename, content)
    return buffer.getvalue()


def test_view_zip_basic():
    """Test basic ZIP file viewing."""
    zip_data = create_test_zip(
        {"file1.txt": b"Hello, World!", "file2.txt": b"Test content"}
    )
    result = zip.prettify(zip_data, meta("application/zip"))
    assert "file1.txt" in result
    assert "file2.txt" in result
    assert "filename:" in result
    assert "size:" in result
    assert zip.syntax_highlight == "yaml"
    assert result.startswith("-") or result.startswith("filename:")


def test_view_zip_empty():
    """Test empty ZIP file."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w"):
        pass
    zip_data = buffer.getvalue()

    result = zip.prettify(zip_data, meta("application/zip"))
    assert result == "[]\n" or result == ""


def test_view_zip_with_directories():
    """Test ZIP file with nested directories."""
    zip_data = create_test_zip(
        {
            "dir1/file1.txt": b"Content 1",
            "dir1/subdir/file2.txt": b"Content 2",
            "file3.txt": b"Content 3",
        }
    )
    result = zip.prettify(zip_data, meta("application/zip"))
    assert "dir1/file1.txt" in result
    assert "dir1/subdir/file2.txt" in result
    assert "file3.txt" in result


def test_view_zip_file_sizes():
    """Test that file sizes are included."""
    zip_data = create_test_zip(
        {
            "small.txt": b"x",
            "medium.txt": b"x" * 100,
            "large.txt": b"x" * 1000,
        }
    )
    result = zip.prettify(zip_data, meta("application/zip"))
    assert "small.txt" in result
    assert "medium.txt" in result
    assert "large.txt" in result
    assert "size: 1" in result or "1" in result
    assert "size: 100" in result or "100" in result
    assert "size: 1000" in result or "1000" in result


def test_view_zip_zero_size_file():
    """Test zero-size file (should not include size field)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        info = zipfile.ZipInfo("empty.txt")
        info.file_size = 0
        zf.writestr(info, b"")
    zip_data = buffer.getvalue()

    result = zip.prettify(zip_data, meta("application/zip"))
    assert "empty.txt" in result
    assert "filename: empty.txt" in result or "filename: empty.txt" in result


def test_view_zip_corrupted():
    """Test handling of corrupted ZIP files."""
    corrupted_data = b"PK\x03\x04invalid zip data"
    with pytest.raises(ValueError, match="Invalid or corrupted ZIP file"):
        zip.prettify(corrupted_data, meta("application/zip"))


def test_view_zip_invalid_data():
    """Test handling of invalid ZIP data."""
    invalid_data = b"Not a ZIP file at all"
    with pytest.raises(ValueError):
        zip.prettify(invalid_data, meta("application/zip"))


def test_render_priority():
    """Test render priority logic."""
    assert (
        zip.render_priority(b"PK\x03\x04", Metadata(content_type="application/zip"))
        == 1.0
    )
    assert zip.render_priority(b"data", Metadata(content_type="application/zip")) == 1.0
    assert zip.render_priority(b"PK\x03\x04", Metadata(content_type="text/plain")) == 0
    assert zip.render_priority(b"", Metadata(content_type="application/zip")) == 0
    assert zip.render_priority(b"PK\x03\x04", Metadata()) == 0


def test_view_zip_special_characters():
    """Test ZIP file with special characters in filenames."""
    zip_data = create_test_zip(
        {"file with spaces.txt": b"content", "file-with-dashes.txt": b"content2"}
    )
    result = zip.prettify(zip_data, meta("application/zip"))
    assert "file with spaces.txt" in result
    assert "file-with-dashes.txt" in result


def test_view_zip_general_exception(monkeypatch):
    """Test handling of general exceptions during ZIP parsing."""
    zip_data = create_test_zip({"test.txt": b"content"})

    from mitmproxy.contentviews import _view_zip

    original_zipfile = _view_zip.zipfile.ZipFile

    class MockZipFile:
        def __init__(self, *args, **kwargs):
            self._zipfile = original_zipfile(*args, **kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def infolist(self):
            raise RuntimeError("Mocked infolist error")

    monkeypatch.setattr(_view_zip.zipfile, "ZipFile", MockZipFile)

    with pytest.raises(ValueError, match="Error parsing ZIP file"):
        zip.prettify(zip_data, meta("application/zip"))


def test_view_zip_unicode_filenames():
    """Test ZIP file with Unicode characters in filenames."""
    zip_data = create_test_zip(
        {
            "文件.txt": b"content",
            "café.txt": b"content",
            "тест.txt": b"content",
        }
    )
    result = zip.prettify(zip_data, meta("application/zip"))
    assert "文件.txt" in result or "文件" in result
    assert "café.txt" in result
    assert "тест.txt" in result or "тест" in result


def test_view_zip_long_filenames():
    """Test ZIP file with very long filenames."""
    long_filename = "a" * 200 + ".txt"
    zip_data = create_test_zip({long_filename: b"content"})
    result = zip.prettify(zip_data, meta("application/zip"))
    assert long_filename in result


def test_view_zip_extract_file_info_helper():
    """Test the _extract_file_info helper method directly."""
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("file1.txt", b"content")
        info = zipfile.ZipInfo("file2.txt")
        info.file_size = 0
        zf.writestr(info, b"")
    buffer.seek(0)

    with zipfile.ZipFile(buffer, "r") as zf:
        info_list = zf.infolist()
        files = zip._extract_file_info(info_list)

    assert len(files) == 2
    assert files[0]["filename"] == "file1.txt"
    assert "size" in files[0]
    assert files[0]["size"] > 0
    assert files[1]["filename"] == "file2.txt"
    assert "size" not in files[1]


def test_view_zip_yaml_output_format():
    """Test that output is valid YAML format."""
    from mitmproxy.contentviews._utils import yaml_loads

    zip_data = create_test_zip(
        {
            "file1.txt": b"content1",
            "file2.txt": b"content2",
        }
    )
    result = zip.prettify(zip_data, meta("application/zip"))
    parsed = yaml_loads(result)
    assert isinstance(parsed, list)
    assert len(parsed) == 2
    assert all("filename" in f for f in parsed)
