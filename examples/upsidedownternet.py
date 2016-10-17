import io
from PIL import Image


def response(flow):
    if flow.response.headers.get("content-type", "").startswith("image"):
        try:
            s = io.StringIO(flow.response.content)
            img = Image.open(s).rotate(180)
            s2 = io.StringIO()
            img.save(s2, "png")
            flow.response.content = s2.getvalue()
            flow.response.headers["content-type"] = "image/png"
        except:  # Unknown image types etc.
            pass
