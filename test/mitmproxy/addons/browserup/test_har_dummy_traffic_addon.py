import pytest
import json
from unittest.mock import MagicMock

from mitmproxy.test import tflow
from mitmproxy.addons.browserup.har_dummy_traffic_addon import (
    HarDummyTrafficAddon,
    set_nested_value
)


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
    obj = {}
    set_nested_value(obj, "items.2.name", "item3")
    assert obj["items"][0] == {}
    assert obj["items"][1] == {}
    assert obj["items"][2]["name"] == "item3"


def test_request_non_devnull():
    # Setup
    addon = HarDummyTrafficAddon()
    flow = tflow.tflow()
    flow.request.host = "example.com"
    
    # Test
    addon.request(flow)
    
    # Verify - should not modify normal flows
    assert flow.response is None


def test_request_devnull_basic():
    # Setup
    addon = HarDummyTrafficAddon()
    flow = tflow.tflow()
    flow.request.host = "dev-null.com"
    flow.request.query = {}
    
    # Test
    addon.request(flow)
    
    # Verify - should create default 204 response
    assert flow.response.status_code == 204
    assert flow.response.content == b""
    assert flow.metadata["har_updates"] == {}


def test_request_devnull_with_status():
    # Setup
    addon = HarDummyTrafficAddon()
    flow = tflow.tflow()
    flow.request.host = "dev-null.com"
    flow.request.query = {"status": "404"}
    
    # Test
    addon.request(flow)
    
    # Verify - should create response with specified status
    assert flow.response.status_code == 404
    assert flow.response.content == b""


def test_request_devnull_with_har_values():
    # Setup
    addon = HarDummyTrafficAddon()
    flow = tflow.tflow()
    flow.request.host = "dev-null.com"
    flow.request.query = {
        "timings.wait": "20",
        "response.bodySize": "1453"
    }
    
    # Test
    addon.request(flow)
    
    # Verify - should store HAR updates in metadata
    assert flow.response.status_code == 204
    assert flow.metadata["har_updates"] == {
        "timings.wait": 20,
        "response.bodySize": 1453
    }


def test_response_updates_har_entry():
    # Setup
    addon = HarDummyTrafficAddon()
    flow = tflow.tflow(resp=True)
    flow.request.host = "dev-null.com"
    
    # Mock a HAR entry on the flow
    flow.har_entry = {
        "timings": {},
        "response": {}
    }
    
    flow.metadata = {
        "har_updates": {
            "timings.wait": 50,
            "response.bodySize": 2000
        }
    }
    
    # Test
    addon.response(flow)
    
    # Verify HAR entry was updated correctly
    assert flow.har_entry["timings"]["wait"] == 50
    assert flow.har_entry["response"]["bodySize"] == 2000


def test_resource_provides_examples():
    # Setup
    from mitmproxy.addons.browserup.har_dummy_traffic_addon import HarDummyResource
    
    addon = HarDummyTrafficAddon()
    resource = HarDummyResource(addon)
    
    req = MagicMock()
    resp = MagicMock()
    
    # Test
    resource.on_get(req, resp)
    
    # Verify response contains examples
    assert resp.content_type == "application/json"
    response_body = json.loads(resp.body.decode('utf-8'))
    assert "examples" in response_body
    assert len(response_body["examples"]) > 0