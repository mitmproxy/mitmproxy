import Image, cStringIO
def response(context, flow):
    if flow.response.headers["content-type"] == ["image/png"]:
        s = cStringIO.StringIO(flow.response.content)
        img = Image.open(s).rotate(180)
        s2 = cStringIO.StringIO()
        img.save(s2, "png")
        flow.response.content = s2.getvalue()
