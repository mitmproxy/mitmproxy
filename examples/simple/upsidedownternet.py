"""
This script rotates all images passing through the proxy by 180 degrees.
"""
import io

from PIL import Image


def response(flow):
    if flow.response.headers.get("content-type", "").startswith("image"):
        s = io.BytesIO(flow.response.content)
        img = Image.open(s).rotate(180)
        s2 = io.BytesIO()
        img.save(s2, "png")
        flow.response.content = s2.getvalue()
        flow.response.headers["content-type"] = "image/png"
