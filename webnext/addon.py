"""
This mitmproxy serves the production build of the mitmwebnext interface and strips the Origin header from all outgoing requests to the mitmweb API.
"""

import os
import mimetypes
from mitmproxy import http

class ServeWebNext:
  def request(self, flow: http.HTTPFlow) -> None:
    # Strip the Origin header from requests to the mitmweb API.
    if "origin" in flow.request.headers:
      flow.request.headers.pop("origin")

    # Serve static assets from dist folder
    request_path = flow.request.path
    
    # Serve index.html on root path
    if request_path == "/":
      request_path = "/index.html"
    
    # Remove leading slash and construct file path
    file_path = request_path.lstrip("/")
    dist_path = os.path.join(os.path.dirname(__file__), "dist", file_path)
    
    if os.path.exists(dist_path) and os.path.isfile(dist_path):
      # Determine content type based on file extension
      content_type, _ = mimetypes.guess_type(dist_path)
      if content_type is None:
        content_type = "application/octet-stream"
      
      # Read file content
      mode = "r" if content_type.startswith("text/") or content_type == "application/javascript" else "rb"
      encoding = "utf-8" if mode == "r" else None
      
      with open(dist_path, mode, encoding=encoding) as f:
        content = f.read()
      
      flow.response = http.Response.make(
        200,
        content,
        {"Content-Type": content_type}
      )
      return

addons = [ServeWebNext()]
