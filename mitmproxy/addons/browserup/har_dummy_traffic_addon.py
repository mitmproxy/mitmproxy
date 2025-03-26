import copy
import json
import logging
import time
import uuid
from datetime import datetime
from datetime import timezone

from mitmproxy import http
from mitmproxy.addons.browserup.har.har_builder import HarBuilder


def set_nested_value(obj, path, value):
    """
    Given a dictionary `obj`, create/overwrite a nested key following dot notation.
    Example: set_nested_value(obj, "response.headers.0.name", "Content-Type")
    """
    parts = path.split(".")
    ref = obj
    for i, part in enumerate(parts):
        is_last = (i == len(parts) - 1)

        # Handle array-like keys: e.g. "headers.0"
        if part.isdigit():
            # Convert string index to int
            idx = int(part)
            if not isinstance(ref, list):
                # Initialize as a list if it's not already one
                if isinstance(ref, dict) and not ref:
                    ref.clear()  # Make sure it's empty
                    ref[part] = []
                    ref = ref[part]
                    continue
                # If we're trying to set an array on something else, just create a new list
                ref = []
                obj[parts[i-1]] = ref  # Reassign to the parent
            
            # Expand list size if needed
            while len(ref) <= idx:
                ref.append({})
            
            if is_last:
                ref[idx] = value
            else:
                if not isinstance(ref[idx], dict) and not isinstance(ref[idx], list):
                    ref[idx] = {}
                ref = ref[idx]
        else:
            # Dictionary key
            if part not in ref or not isinstance(ref[part], (dict, list)):
                # Create nested dict if needed
                if not is_last:
                    ref[part] = {}
            if is_last:
                # Final key gets the value
                ref[part] = value
            else:
                ref = ref[part]
    return obj


class HarDummyResource:
    def addon_path(self):
        return "har/dummy/example"

    def __init__(self, dummy_addon):
        self.dummy_addon = dummy_addon

    def on_get(self, req, resp):
        """
        Example endpoint to explain dummy traffic feature
        ---
        description: Example of how to use the dummy traffic feature
        operationId: getDummyTrafficExample
        tags:
            - BrowserUpProxy
        responses:
            200:
                description: Success - Returns example usage
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                examples:
                                    type: array
                                    items:
                                        type: string
                                description:
                                    type: string
                                defaultValues:
                                    type: object
        """
        examples = {
            "description": "The dev-null.com domain is reserved for dummy traffic. Any requests to this domain will be intercepted and used to create HAR entries with custom values.",
            
            "examples": [
                "http://dev-null.com/any/path",
                "http://dev-null.com/any/path?timings.wait=150",
                "http://dev-null.com/any/path?status=404&timings.wait=20&response.bodySize=1453",
                "http://dev-null.com/any/path?response.headers.0.name=Content-Type&response.headers.0.value=application/json"
            ],
            
            "defaultValues": {
                "General structure": "A default HAR entry is automatically created with reasonable values for timings, sizes, etc.",
                "Request": "Includes method, URL, HTTP version, headers, etc.",
                "Response": "Includes status code, headers, content info, etc.",
                "Timings": "Includes reasonable values for send, wait, receive times",
                "Other": "Includes server IP, connection ID, etc."
            },
            
            "commonCustomizations": {
                "status": "HTTP status code (e.g., 200, 404, 500)",
                "timings.wait": "Time waiting for server response in ms",
                "timings.receive": "Time downloading response in ms",
                "response.bodySize": "Size of response body in bytes",
                "response.content.size": "Size of content in bytes",
                "response.content.mimeType": "MIME type of response (e.g., 'application/json')"
            }
        }
        
        resp.content_type = "application/json"
        resp.body = json.dumps(examples).encode('utf-8')


def create_default_har_entry(url, method="GET", status_code=200):
    """
    Create a default HAR entry with reasonable values that can be overridden.
    """
    now = datetime.now(timezone.utc).isoformat()
    req_start_time = time.time() - 1  # 1 second ago
    req_end_time = time.time()
    
    # Calculate some reasonable default timing values
    total_time = int((req_end_time - req_start_time) * 1000)  # milliseconds
    wait_time = int(total_time * 0.6)  # 60% of time in wait
    receive_time = int(total_time * 0.3)  # 30% in receive
    send_time = total_time - wait_time - receive_time  # remainder in send
    
    # Use UUID for unique IDs
    connection_id = str(uuid.uuid4())
    
    # Create default HAR entry using HarBuilder for consistency
    har_entry = HarBuilder.entry()
    
    # Override with sensible defaults
    har_entry.update({
        "startedDateTime": now,
        "time": total_time,
        "request": {
            "method": method,
            "url": url,
            "httpVersion": "HTTP/1.1",
            "cookies": [],
            "headers": [
                {"name": "Host", "value": "dev-null.com"},
                {"name": "User-Agent", "value": "BrowserUp-DummyTraffic/1.0"},
                {"name": "Accept", "value": "*/*"}
            ],
            "queryString": [],
            "headersSize": 250,
            "bodySize": 0,
        },
        "response": {
            "status": status_code,
            "statusText": "OK" if status_code == 200 else "",
            "httpVersion": "HTTP/1.1",
            "cookies": [],
            "headers": [
                {"name": "Content-Type", "value": "text/plain"},
                {"name": "Content-Length", "value": "0"},
                {"name": "Date", "value": now}
            ],
            "content": {
                "size": 0,
                "mimeType": "text/plain",
                "text": "",
            },
            "redirectURL": "",
            "headersSize": 150,
            "bodySize": 0,
        },
        "cache": {},
        "timings": {
            "blocked": 0,
            "dns": 0,
            "connect": 0, 
            "ssl": 0,
            "send": send_time,
            "wait": wait_time,
            "receive": receive_time,
        },
        "serverIPAddress": "127.0.0.1",
        "connection": connection_id,
    })
    
    return har_entry


class HarDummyTrafficAddon:
    def __init__(self):
        self.har_manager = None

    def load(self, loader):
        logging.info("Loading HarDummyTrafficAddon")

    def configure(self, updated):
        pass

    def get_resources(self):
        return [HarDummyResource(self)]

    def request(self, flow: http.HTTPFlow):
        # Only handle dev-null.com domain
        if not flow.request.pretty_host.lower().endswith("dev-null.com"):
            return

        # Default status code
        status_code = 204
        har_updates = {}

        # Parse query string for HAR customizations
        for key, val in flow.request.query.items():
            if key == "status":
                # Override status code
                try:
                    status_code = int(val)
                except ValueError:
                    status_code = 204  # Default if value is not a valid integer
            else:
                # Convert to appropriate type (int or float if possible)
                try:
                    if "." in val:
                        numeric_val = float(val)
                    else:
                        numeric_val = int(val)
                    val = numeric_val
                except ValueError:
                    pass  # Keep as string if not numeric
                
                # Store the key-value pair for HAR customization
                har_updates[key] = val

        # Add minimal headers
        headers = {"Content-Type": "text/plain"}
        
        # Short-circuit the flow with an empty body
        flow.response = http.Response.make(
            status_code,
            b"",  # empty body
            headers
        )

        # Create a default HAR entry that will be populated later
        flow.metadata["dummy_har_entry"] = create_default_har_entry(
            url=flow.request.url,
            method=flow.request.method,
            status_code=status_code
        )

        # Store the HAR updates in flow.metadata so we can apply them in the response hook
        flow.metadata["har_updates"] = har_updates
        logging.info(f"Created dummy response with HAR updates: {har_updates}")

    def response(self, flow: http.HTTPFlow):
        # Only process requests to dev-null.com
        if not flow.request.pretty_host.lower().endswith("dev-null.com"):
            return

        # Check if we have a default HAR entry from our request handler
        if "dummy_har_entry" not in flow.metadata:
            logging.warning("No dummy HAR entry found in flow metadata")
            return

        # Access the har_entry directly from the flow (added by flow_har_entry_patch)
        if not hasattr(flow, "har_entry"):
            logging.warning("Flow has no har_entry attribute, cannot apply HAR updates")
            return

        # Copy our default HAR entry to the real HAR entry
        default_har = flow.metadata["dummy_har_entry"] 
        har_entry = flow.har_entry
        
        # Apply all values from our default HAR to the real HAR entry
        # This is a deep update that preserves existing nested structures
        for key, value in default_har.items():
            if key in har_entry and isinstance(har_entry[key], dict) and isinstance(value, dict):
                # Deep update dictionaries
                har_entry[key].update(value)
            else:
                # Otherwise, just replace the value
                har_entry[key] = copy.deepcopy(value)
        
        # Apply any custom updates from query parameters
        if "har_updates" in flow.metadata:
            har_updates = flow.metadata["har_updates"]
            
            # Apply each update to the HAR entry using dot notation
            for path, value in har_updates.items():
                if "." in path:
                    # Handle dot notation for nested fields
                    set_nested_value(har_entry, path, value)
                else:
                    # Handle simple top-level fields
                    har_entry[path] = value
                    
            logging.info(f"Applied HAR updates to entry: {har_updates}")
        
        logging.info("Successfully updated HAR entry with default values and custom overrides")


addons = [HarDummyTrafficAddon()]