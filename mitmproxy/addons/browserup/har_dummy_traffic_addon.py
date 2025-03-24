import logging
import json
from urllib.parse import parse_qsl
import copy

from mitmproxy import http


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
                ref[:] = []  # or initialize list if needed
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
                                example:
                                    type: string
        """
        examples = {
            "examples": [
                "http://dev-null.com/any/path?timings.wait=20&response.bodySize=1453",
                "http://dev-null.com/any/path?status=404&timings.wait=20&response.bodySize=1453",
                "http://dev-null.com/any/path?response.headers.0.name=Content-Type&response.headers.0.value=application/json"
            ],
            "description": "The dev-null.com domain is reserved for dummy traffic. Any requests to this domain will be intercepted and used to create HAR entries with custom values."
        }
        resp.content_type = "application/json"
        resp.body = json.dumps(examples).encode('utf-8')


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

        # Store the HAR updates in flow.metadata so we can apply them in the response hook
        flow.metadata["har_updates"] = har_updates
        logging.info(f"Created dummy response with HAR updates: {har_updates}")

    def response(self, flow: http.HTTPFlow):
        # Only process requests to dev-null.com that have HAR updates
        if not flow.request.pretty_host.lower().endswith("dev-null.com") or "har_updates" not in flow.metadata:
            return

        # Access the har_entry directly from the flow (added by flow_har_entry_patch)
        if not hasattr(flow, "har_entry"):
            logging.warning("Flow has no har_entry attribute, cannot apply HAR updates")
            return

        har_entry = flow.har_entry
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


addons = [HarDummyTrafficAddon()]