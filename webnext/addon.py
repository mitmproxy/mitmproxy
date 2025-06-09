"""
This mitmproxy serves the production build of the mitmwebnext interface and strips the Origin header from all outgoing requests to the mitmweb API.
"""

import os
import mimetypes
from mitmproxy import http

class ServeWebNext:
  def __init__(self):
    # Walk the dist directory and collect all available files
    self.available_files = set()
    dist_dir = os.path.join(os.path.dirname(__file__), "dist")
    if os.path.exists(dist_dir):
      for root, dirs, files in os.walk(dist_dir):
        for file in files:
          rel_path = os.path.relpath(os.path.join(root, file), dist_dir)
          url_path = "/" + rel_path.replace(os.path.sep, "/")
          self.available_files.add(url_path)

  def request(self, flow: http.HTTPFlow) -> None:
    # Strip the Origin header from requests to the mitmweb API.
    if "origin" in flow.request.headers:
      flow.request.headers.pop("origin")

    # Serve all files from dist folder statically
    request_path = flow.request.path
    file_path = None
    
    # Check if requested path matches any file in dist directory
    if request_path in self.available_files:
      file_path = request_path.lstrip("/")
    elif request_path == "/":
      file_path = "index.html"

    if file_path is not None:
      dist_path = os.path.join(os.path.dirname(__file__), "dist", file_path)

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

addons = [ServeWebNext()]
