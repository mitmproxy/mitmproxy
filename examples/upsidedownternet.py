import cStringIO
from PIL import Image
from libmproxy.protocol.http import decoded

def response(context, flow):
    if flow.response.headers.get_first("content-type", "").startswith("image"):
        with decoded(flow.response):  # automatically decode gzipped responses.
            try:
                s = cStringIO.StringIO(flow.response.content)
                img = Image.open(s).rotate(180)
                s2 = cStringIO.StringIO()
                img.save(s2, "png")
                flow.response.content = s2.getvalue()
                flow.response.headers["content-type"] = ["image/png"]
            except:  # Unknown image types etc.
                pass