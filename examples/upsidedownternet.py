from six.moves import cStringIO as StringIO
from PIL import Image
from mitmproxy.models import decoded


def response(context, flow):
    if flow.response.headers.get("content-type", "").startswith("image"):
        with decoded(flow.response):  # automatically decode gzipped responses.
            try:
                s = StringIO(flow.response.content)
                img = Image.open(s).rotate(180)
                s2 = StringIO()
                img.save(s2, "png")
                flow.response.content = s2.getvalue()
                flow.response.headers["content-type"] = "image/png"
            except:  # Unknown image types etc.
                pass
