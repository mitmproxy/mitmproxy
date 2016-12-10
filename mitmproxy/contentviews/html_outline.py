import html2text

from mitmproxy.contentviews import base


class ViewHTMLOutline(base.View):
    name = "HTML Outline"
    prompt = ("html outline", "o")
    content_types = ["text/html"]

    def __call__(self, data, **metadata):
        data = data.decode("utf-8", "replace")
        h = html2text.HTML2Text(baseurl="")
        h.ignore_images = True
        h.body_width = 0
        outline = h.handle(data)
        return "HTML Outline", base.format_text(outline)
