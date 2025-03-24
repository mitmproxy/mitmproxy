import pytest

from mitmproxy import http
from mitmproxy.addons.browserup import har_capture_addon
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.test import tutils


class TestHARMetrics:
    def test_metric_added(self, hc, flow):
        hc.add_metric_to_har({"name": "time-to-first-paint", "value": 3})
        assert len(hc.get_or_create_current_page().get("_metrics")) == 1

    def test_valid_metrics_added(self, hc, flow):
        hc.add_metric_to_har({"name": "time-to-first-byte", "value": 1})
        hc.add_metric_to_har({"name": "time-to-first-paint", "value": 2})
        metrics = hc.get_or_create_current_page().get("_metrics")
        assert len(metrics) == 2
        assert metrics[0].get("name") == "time-to-first-byte"
        assert metrics[0].get("value") == 1
        assert metrics[1].get("name") == "time-to-first-paint"
        assert metrics[1].get("value") == 2

    def test_valid_metric_added_then_reset(self, hc, flow):
        hc.add_metric_to_har({"name": "time-to-first-byte", "value": 1})
        hc.add_metric_to_har({"name": "time-to-first-paint", "value": 2})
        hc.new_page("page1", "New Page!")
        assert hc.get_or_create_current_page().get("_metrics") is None
        hc.add_metric_to_har({"name": "time-to-first-byte", "value": 1})
        metrics = hc.get_or_create_current_page().get("_metrics")
        assert len(metrics) == 1

    def test_new_har_empty_metrics(self, hc, flow):
        hc.add_metric_to_har({"name": "time-to-first-byte", "value": 1})
        hc.add_metric_to_har({"name": "time-to-first-paint", "value": 2})
        hc.reset_har_and_return_old_har()
        hc.new_page("page1", "New Page!")
        assert hc.get_or_create_current_page().get("_metrics") is None


@pytest.fixture()
def flow():
    resp_content = b"message"
    times = dict(
        timestamp_start=746203200,
        timestamp_end=746203290,
    )

    return tflow.tflow(
        req=tutils.treq(method=b"GET", **times),
        resp=tutils.tresp(content=resp_content, **times),
    )


@pytest.fixture()
def json_flow():
    times = dict(
        timestamp_start=746203200,
        timestamp_end=746203290,
    )

    return tflow.tflow(
        req=tutils.treq(method=b"GET", path=b"/path/foo.json", **times),
        resp=tutils.tresp(
            content=b'{"foo": "bar"}',
            headers=http.Headers(
                (
                    (b"header-response", b"svalue"),
                    (b"content-type", b"application/json"),
                )
            ),
            **times,
        ),
    )


@pytest.fixture()
def hc(flow):
    a = har_capture_addon.HarCaptureAddOn()
    with taddons.context(hc) as ctx:
        ctx.configure(a)
    return a
