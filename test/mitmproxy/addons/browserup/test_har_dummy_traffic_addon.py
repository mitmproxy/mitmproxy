import json
from unittest.mock import MagicMock

import pytest

from mitmproxy.addons.browserup.har_dummy_traffic_addon import create_default_har_entry
from mitmproxy.addons.browserup.har_dummy_traffic_addon import HarDummyResource
from mitmproxy.addons.browserup.har_dummy_traffic_addon import HarDummyTrafficAddon
from mitmproxy.addons.browserup.har_dummy_traffic_addon import set_nested_value
from mitmproxy.test import taddons
from mitmproxy.test import tflow


def test_set_nested_value_basic_dict():
    obj = {}
    set_nested_value(obj, "a", 1)
    assert obj == {"a": 1}


def test_set_nested_value_nested_dict():
    obj = {}
    set_nested_value(obj, "a.b.c", 1)
    assert obj == {"a": {"b": {"c": 1}}}


def test_set_nested_value_array_index():
    obj = {"items": []}
    set_nested_value(obj, "items.0.name", "item1")
    assert obj == {"items": [{"name": "item1"}]}


def test_set_nested_value_create_arrays_with_gaps():
    obj = {"items": []}  # Initialize with an empty array
    set_nested_value(obj, "items.2.name", "item3")
    assert obj["items"][0] == {}
    assert obj["items"][1] == {}
    assert obj["items"][2]["name"] == "item3"


def test_request_non_devnull(dummy_addon):
    # Setup
    flow = tflow.tflow()
    flow.request.host = "example.com"
    
    # Test
    dummy_addon.request(flow)
    
    # Verify - should not modify normal flows
    assert flow.response is None


def test_request_devnull_basic(dummy_addon):
    # Setup
    flow = tflow.tflow()
    flow.request.host = "dev-null.com"
    flow.request.query = {}
    
    # Test
    dummy_addon.request(flow)
    
    # Verify - should create default 204 response
    assert flow.response.status_code == 204
    assert flow.response.content == b""
    assert flow.metadata["har_updates"] == {}
    assert "dummy_har_entry" in flow.metadata


def test_request_devnull_with_status(dummy_addon):
    # Setup
    flow = tflow.tflow()
    flow.request.host = "dev-null.com"
    flow.request.query = {"status": "404"}
    
    # Test
    dummy_addon.request(flow)
    
    # Verify - should create response with specified status
    assert flow.response.status_code == 404
    assert flow.response.content == b""


def test_request_devnull_with_har_values(dummy_addon):
    # Setup
    flow = tflow.tflow()
    flow.request.host = "dev-null.com"
    flow.request.query = {
        "timings.wait": "20",
        "response.bodySize": "1453"
    }
    
    # Test
    dummy_addon.request(flow)
    
    # Verify - should store HAR updates in metadata
    assert flow.response.status_code == 204
    assert flow.metadata["har_updates"] == {
        "timings.wait": 20,
        "response.bodySize": 1453
    }


def test_response_updates_har_entry(dummy_addon):
    # Setup
    flow = tflow.tflow(resp=True)
    flow.request.host = "dev-null.com"
    
    # Mock a HAR entry on the flow
    flow.har_entry = {
        "timings": {},
        "response": {}
    }
    
    # Create a dummy HAR entry and apply updates
    flow.metadata = {
        "dummy_har_entry": create_default_har_entry(url=flow.request.url),
        "har_updates": {
            "timings.wait": 50,
            "response.bodySize": 2000
        }
    }
    
    # Test
    dummy_addon.response(flow)
    
    # Verify HAR entry was updated with both default values and custom overrides
    assert flow.har_entry["timings"]["wait"] == 50  # Custom override
    assert flow.har_entry["response"]["bodySize"] == 2000  # Custom override
    assert flow.har_entry["request"]["method"] == "GET"  # Default value
    assert "serverIPAddress" in flow.har_entry  # Default value
    assert len(flow.har_entry["request"]["headers"]) > 0  # Default headers


def test_create_default_har_entry():
    # Create a default HAR entry
    url = "http://example.com/test"
    har_entry = create_default_har_entry(url=url, method="POST", status_code=201)
    
    # Verify it has the correct structure and values
    assert har_entry["request"]["url"] == url
    assert har_entry["request"]["method"] == "POST"
    assert har_entry["response"]["status"] == 201
    assert "timings" in har_entry
    for key in ["send", "wait", "receive"]:
        assert key in har_entry["timings"]
    assert "serverIPAddress" in har_entry
    assert "connection" in har_entry


def test_resource_provides_examples(dummy_addon):
    # Setup
    resource = HarDummyResource(dummy_addon)
    
    req = MagicMock()
    resp = MagicMock()
    
    # Test
    resource.on_get(req, resp)
    
    # Verify response contains examples and documentation
    assert resp.content_type == "application/json"
    response_body = json.loads(resp.body.decode('utf-8'))
    assert "examples" in response_body
    assert len(response_body["examples"]) > 0
    assert "defaultValues" in response_body
    assert "commonCustomizations" in response_body


@pytest.fixture()
def dummy_addon():
    a = HarDummyTrafficAddon()
    with taddons.context(a) as ctx:
        ctx.configure(a)
    return a