import pytest

from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews._view_csv import csv_view


def test_view_csv():
    meta = Metadata()
    assert csv_view.syntax_highlight == "none"
    assert csv_view.name == "CSV"

    # Valid multi-row CSV
    data = b"name,age,city\nAlice,30,London\nBob,25,Paris\n"
    res = csv_view.prettify(data, meta)
    assert "name  | age | city" in res
    assert "------+-----+-------" in res
    assert "Alice | 30  | London" in res
    assert "Bob   | 25  | Paris" in res

    # Single row (no separator line)
    single = b"col1,col2,col3\n"
    res_single = csv_view.prettify(single, meta)
    assert "col1 | col2 | col3" in res_single
    assert "-+-" not in res_single

    # TSV with tab delimiter specified in content-type
    tsv_meta = Metadata(content_type="text/tab-separated-values")
    tsv_data = b"id\tvalue\n1\talpha\n2\tbeta\n"
    res_tsv = csv_view.prettify(tsv_data, tsv_meta)
    assert "id | value" in res_tsv
    assert "1  | alpha" in res_tsv

    # Semicolon delimited (auto-sniffed)
    semi_data = b"a;b;c\n1;2;3\n4;5;6\n"
    res_semi = csv_view.prettify(semi_data, meta)
    assert "a | b | c" in res_semi
    assert "1 | 2 | 3" in res_semi

    # Empty and whitespace
    assert csv_view.prettify(b"", meta) == ""
    assert csv_view.prettify(b"   \n\t  \n", meta) == ""
    assert csv_view.prettify(b",,,\n,,,\n", meta) == ""

    # Uneven column counts
    uneven = b"a,b,c\n1\n2,3\n"
    res_uneven = csv_view.prettify(uneven, meta)
    assert "a | b | c" in res_uneven
    assert "1" in res_uneven


def test_view_csv_error(monkeypatch):
    import csv

    def mock_reader(*args, **kwargs):
        raise csv.Error("malformed")

    monkeypatch.setattr(csv, "reader", mock_reader)
    with pytest.raises(ValueError, match="Invalid CSV"):
        csv_view.prettify(b"a,b\n1,2", Metadata())


def test_render_priority():
    assert csv_view.render_priority(b"data", Metadata(content_type="text/csv")) == 1
    assert (
        csv_view.render_priority(
            b"data", Metadata(content_type="text/tab-separated-values")
        )
        == 1
    )
    assert csv_view.render_priority(b"data", Metadata(content_type="text/tsv")) == 1
    assert (
        csv_view.render_priority(b"data", Metadata(content_type="application/csv")) == 1
    )
    assert csv_view.render_priority(b"data", Metadata(content_type="text/x-csv")) == 1
    assert csv_view.render_priority(b"data", Metadata(content_type="text/x-tsv")) == 1
    assert (
        csv_view.render_priority(b"data", Metadata(content_type="application/json"))
        == 0
    )
    assert csv_view.render_priority(b"data", Metadata(content_type="text/plain")) == 0
    assert csv_view.render_priority(b"", Metadata(content_type="text/csv")) == 0
    assert csv_view.render_priority(b"data", Metadata(content_type=None)) == 0
