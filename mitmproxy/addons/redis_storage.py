"""Redis storage addon for mitmproxy.

This addon provides Redis storage capabilities for mitmproxy flows, allowing for
persistent storage and efficient querying of intercepted HTTP/HTTPS traffic.
"""

import json
import os
import re
import time

import redis

from mitmproxy import ctx
from mitmproxy import http

# Redis connection details
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 1))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)
REDIS_SSL = os.environ.get("REDIS_SSL", "false").lower() == "true"
REDIS_FLOWS_KEY = os.environ.get("REDIS_FLOWS_KEY", "mitmproxy:flows")
REDIS_ENABLED = os.environ.get("REDIS_ENABLED", "true").lower() == "true"


class RedisStorage:
    """Store flows in Redis for persistence and efficient querying."""

    def __init__(self):
        self.redis_client = None
        self.request_count = 0

    def load(self, loader):
        """Called when the addon is loaded."""
        if not REDIS_ENABLED:
            ctx.log.info("Redis storage is disabled by environment configuration")
            return

        self.setup_redis_connection()

    def setup_redis_connection(self):
        """Set up connection to Redis server."""
        try:
            ctx.log.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}")

            # Create Redis connection with optional SSL
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                ssl=REDIS_SSL,
                ssl_cert_reqs=None
                if REDIS_SSL
                else None,  # Skip certificate verification if SSL enabled
                decode_responses=True,  # Enable automatic decoding for hash operations
                retry_on_timeout=True,
                socket_keepalive=True,
            )

            # Test connection
            self.redis_client.ping()
            ctx.log.info("Successfully connected to Redis")

        except Exception as e:
            ctx.log.error(f"Error connecting to Redis: {e}")
            self.redis_client = None

    def normalize_path(self, path: str) -> str:
        """Normalize a URL path for Redis key storage.

        Examples:
            /v7/couriers/9ccf1938-d59d-407a-ae4d-24cd56c49319/sync -> /v7/couriers/*/sync
            /v1/couriers/9ccf1938-d59d-407a-ae4d-24cd56c49319/location -> /v1/couriers/*/location
            /orders/123456/status -> /orders/*/status
        """
        # Replace UUIDs with *
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "*",
            path,
            flags=re.IGNORECASE,
        )

        # Replace numeric IDs with *
        path = re.sub(r"/\d+(?=/|$)", "/*", path)

        # Remove query parameters
        path = path.split("?")[0]

        # Remove trailing slash if present
        path = path.rstrip("/")

        return path

    def request(self, flow: http.HTTPFlow) -> None:
        """Handle incoming request."""
        if not self.redis_client:
            return

        self.request_count += 1
        flow.metadata["captured_time"] = time.time()

    def response(self, flow: http.HTTPFlow) -> None:
        """Handle incoming response."""
        if not self.redis_client:
            return

        # Skip flows that weren't captured in the request phase
        if "captured_time" not in flow.metadata:
            return

        # Save the flow to Redis
        self.save_flow(flow)

    def save_flow(self, flow: http.HTTPFlow) -> None:
        """Save request/response flow to Redis."""
        try:
            # Safely decode request and response content
            try:
                request_content = (
                    flow.request.content.decode("utf-8", "ignore")
                    if flow.request.content
                    else None
                )
            except Exception as e:
                ctx.log.warning(f"Could not decode request content: {e}")
                request_content = None

            try:
                response_content = (
                    flow.response.content.decode("utf-8", "ignore")
                    if flow.response and flow.response.content
                    else None
                )
            except Exception as e:
                ctx.log.warning(f"Could not decode response content: {e}")
                response_content = None

            # Prepare flow data structure
            flow_data = {
                "url": flow.request.pretty_url,
                "method": flow.request.method,
                "host": flow.request.host,
                "path": flow.request.path,
                "normalized_path": self.normalize_path(flow.request.path),
                "request_headers": dict(flow.request.headers),
                "request_content": request_content,
                "status_code": flow.response.status_code if flow.response else None,
                "response_headers": dict(flow.response.headers)
                if flow.response
                else None,
                "response_content": response_content,
                "content_type": flow.response.headers.get("content-type", "")
                if flow.response
                else None,
                "content_length": len(flow.response.content)
                if flow.response and flow.response.content
                else 0,
                "timestamp": flow.request.timestamp_start,
                "response_time": time.time() - flow.request.timestamp_start,
                "flow_id": self.request_count,
                "client_ip": flow.client_conn.peername[0]
                if flow.client_conn and flow.client_conn.peername
                else "unknown",
                "captured_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "is_api": "api" in flow.request.host.lower()
                if flow.request.host
                else False,
                "has_response": flow.response is not None,
                "is_success": flow.response and 200 <= flow.response.status_code < 300
                if flow.response
                else False,
                "is_error": flow.response and flow.response.status_code >= 400
                if flow.response
                else False,
                "is_secure": flow.request.scheme == "https",
            }

            # Create a unique key for this flow using the normalized path
            timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            flow_key = f"{REDIS_FLOWS_KEY}:{flow_data['normalized_path']}:{timestamp}:{flow_data['host']}:{flow_data['method']}:{flow_data['flow_id']}"

            # Store flow data as JSON string
            self.redis_client.set(flow_key, json.dumps(flow_data))

            # Set expiration (7 days)
            self.redis_client.expire(flow_key, 60 * 60 * 24 * 7)

            # Add to a sorted set for time-based retrieval
            self.redis_client.zadd(
                f"{REDIS_FLOWS_KEY}:by_time", {flow_key: flow_data["timestamp"]}
            )

            # Add to a set for each normalized path
            self.redis_client.sadd(
                f"{REDIS_FLOWS_KEY}:paths", flow_data["normalized_path"]
            )
            self.redis_client.sadd(
                f"{REDIS_FLOWS_KEY}:by_path:{flow_data['normalized_path']}", flow_key
            )

            # Add to a set for each domain
            if flow_data["host"]:
                self.redis_client.sadd(f"{REDIS_FLOWS_KEY}:domains", flow_data["host"])
                self.redis_client.sadd(
                    f"{REDIS_FLOWS_KEY}:by_domain:{flow_data['host']}", flow_key
                )

            # Add to a set for each HTTP method
            self.redis_client.sadd(f"{REDIS_FLOWS_KEY}:methods", flow_data["method"])
            self.redis_client.sadd(
                f"{REDIS_FLOWS_KEY}:by_method:{flow_data['method']}", flow_key
            )

            # Add to a set for status code ranges (2xx, 4xx, 5xx)
            if flow_data["status_code"]:
                status_range = f"{flow_data['status_code'] // 100}xx"
                self.redis_client.sadd(f"{REDIS_FLOWS_KEY}:status_ranges", status_range)
                self.redis_client.sadd(
                    f"{REDIS_FLOWS_KEY}:by_status:{status_range}", flow_key
                )

            # Trim the sorted set to keep only the last 5000 flows
            self.redis_client.zremrangebyrank(f"{REDIS_FLOWS_KEY}:by_time", 0, -5001)

            ctx.log.info(f"Saved flow to Redis with key: {flow_key}")

            # Publish notification to a channel for real-time monitoring
            self.redis_client.publish(f"{REDIS_FLOWS_KEY}:channel", flow_key)

        except Exception as e:
            ctx.log.error(f"Error saving flow to Redis: {e}")
            ctx.log.error(f"Error details: {str(e)}")


addons = [RedisStorage()]
