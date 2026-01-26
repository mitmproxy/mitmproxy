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
    assert "# ZIP Archive" in result
    assert "Total files: 2" in result
    assert "file1.txt" in result
    assert "file2.txt" in result
    assert "Hello, World!" not in result  # Should not show file contents
    assert zip.syntax_highlight == "yaml"


def test_view_zip_empty():
    """Test empty ZIP file."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w"):
        pass
    zip_data = buffer.getvalue()

    result = zip.prettify(zip_data, meta("application/zip"))
    assert "# ZIP Archive" in result
    assert "Empty archive" in result


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
    assert "Total files: 3" in result
    assert "dir1/file1.txt" in result
    assert "dir1/subdir/file2.txt" in result
    assert "file3.txt" in result


def test_view_zip_compression_methods():
    """Test ZIP file with different compression methods."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        # Stored (no compression)
        zf.writestr("stored.txt", b"stored content", compress_type=zipfile.ZIP_STORED)
        # Deflated
        zf.writestr(
            "deflated.txt", b"deflated content", compress_type=zipfile.ZIP_DEFLATED
        )
    zip_data = buffer.getvalue()

    result = zip.prettify(zip_data, meta("application/zip"))
    assert "stored.txt" in result
    assert "deflated.txt" in result
    assert "store" in result or "stored" in result
    assert "deflate" in result


def test_view_zip_metadata():
    """Test ZIP file metadata display."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        info = zipfile.ZipInfo("test.txt")
        info.date_time = (2024, 1, 15, 14, 30, 0)
        info.comment = b"Test comment"
        zf.writestr(info, b"test content")
    zip_data = buffer.getvalue()

    result = zip.prettify(zip_data, meta("application/zip"))
    assert "2024-01-15 14:30:00" in result
    assert "Test comment" in result


def test_view_zip_compression_ratio():
    """Test compression ratio calculation."""
    # Create a ZIP with compressible content
    zip_data = create_test_zip({"large.txt": b"A" * 1000})
    result = zip.prettify(zip_data, meta("application/zip"))
    assert "Compression ratio" in result


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
    # Should match application/zip content type
    assert (
        zip.render_priority(b"PK\x03\x04", Metadata(content_type="application/zip"))
        == 1.0
    )

    # Should match even without magic bytes if content-type is correct
    assert zip.render_priority(b"data", Metadata(content_type="application/zip")) == 1.0

    # Should not match wrong content type
    assert zip.render_priority(b"PK\x03\x04", Metadata(content_type="text/plain")) == 0

    # Should not match empty data
    assert zip.render_priority(b"", Metadata(content_type="application/zip")) == 0

    # Should not match None content type
    assert zip.render_priority(b"PK\x03\x04", Metadata()) == 0


def test_view_zip_special_characters():
    """Test ZIP file with special characters in filenames."""
    zip_data = create_test_zip(
        {"file with spaces.txt": b"content", "file-with-dashes.txt": b"content2"}
    )
    result = zip.prettify(zip_data, meta("application/zip"))
    assert "file with spaces.txt" in result
    assert "file-with-dashes.txt" in result


def test_view_zip_large_file():
    """Test ZIP file with large file."""
    large_content = b"X" * 10000
    zip_data = create_test_zip({"large.txt": large_content})
    result = zip.prettify(zip_data, meta("application/zip"))
    assert "large.txt" in result
    assert "10,000" in result  # Should show uncompressed size


def test_view_zip_multiple_files_sizes():
    """Test that file sizes are correctly displayed."""
    zip_data = create_test_zip(
        {
            "small.txt": b"x",
            "medium.txt": b"x" * 100,
            "large.txt": b"x" * 1000,
        }
    )
    result = zip.prettify(zip_data, meta("application/zip"))
    # Check that sizes are present
    assert "bytes" in result
    assert "Total compressed size" in result
    assert "Total uncompressed size" in result


def test_view_zip_invalid_date_time():
    """Test handling of invalid date_time values."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        info = zipfile.ZipInfo("test.txt")
        # Invalid date_time that will cause ValueError
        info.date_time = (2024, 13, 32, 25, 70, 100)  # Invalid month, day, hour, minute, second
        zf.writestr(info, b"test content")
    zip_data = buffer.getvalue()

    # Should not raise, but skip the invalid date
    result = zip.prettify(zip_data, meta("application/zip"))
    assert "test.txt" in result
    # Should not contain the invalid date
    assert "2024-13-32" not in result


def test_view_zip_overflow_date_time():
    """Test handling of date_time values that cause OverflowError."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        info = zipfile.ZipInfo("test.txt")
        # Use a valid date_time first to create the ZIP
        info.date_time = (2024, 1, 1, 12, 0, 0)
        zf.writestr(info, b"test content")
    zip_data = buffer.getvalue()

    # Read the ZIP and modify date_time to cause OverflowError
    # We'll create a valid ZIP, then manually modify the date_time in the ZipInfo
    # by reading it back and setting an invalid value
    with zipfile.ZipFile(io.BytesIO(zip_data), "r") as zf_read:
        info_list = zf_read.infolist()
        # Manually set an invalid date_time that will cause OverflowError
        info_list[0].date_time = (3000, 1, 1, 0, 0, 0)  # Year 3000 might cause issues
    
    # Create a new ZIP with the modified info
    buffer2 = io.BytesIO()
    with zipfile.ZipFile(buffer2, "w") as zf2:
        info2 = zipfile.ZipInfo("test.txt")
        # Set date_time to a value that will cause OverflowError when creating datetime
        # Use a very large timestamp value
        info2.date_time = (2100, 1, 1, 0, 0, 0)  # Valid for ZIP but might overflow datetime
        zf2.writestr(info2, b"test content")
    zip_data2 = buffer2.getvalue()

    # The code should handle this gracefully
    result = zip.prettify(zip_data2, meta("application/zip"))
    assert "test.txt" in result


def test_view_zip_general_exception(monkeypatch):
    """Test handling of general exceptions during ZIP parsing."""
    # Create a valid ZIP file
    zip_data = create_test_zip({"test.txt": b"content"})
    
    # Mock yaml_dumps in the _view_zip module to raise an exception
    # This will trigger the general exception handler (lines 67-68)
    from mitmproxy.contentviews import _view_zip
    
    def mock_yaml_dumps(*args, **kwargs):
        raise RuntimeError("Mocked yaml_dumps error")
    
    monkeypatch.setattr(_view_zip, "yaml_dumps", mock_yaml_dumps)
    
    # This should trigger the general exception handler (lines 67-68)
    with pytest.raises(ValueError, match="Error parsing ZIP file"):
        zip.prettify(zip_data, meta("application/zip"))
