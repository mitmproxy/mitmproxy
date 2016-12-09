import html2text
import lxml.etree
import lxml.html

from mitmproxy.contentviews.base import View, format_text
from mitmproxy.utils import strutils


class ViewHTML(View):
    name = "HTML"
    prompt = ("html", "h")
    content_types = ["text/html"]

    def __call__(self, data, **metadata):
        if strutils.is_xml(data):
            parser = lxml.etree.HTMLParser(
                strip_cdata=True,
                remove_blank_text=True
            )
            d = lxml.html.fromstring(data, parser=parser)
            docinfo = d.getroottree().docinfo
            s = lxml.etree.tostring(
                d,
                pretty_print=True,
                doctype=docinfo.doctype,
                encoding='utf8'
            )
            return "HTML", format_text(s)


class ViewHTMLOutline(View):
    name = "HTML Outline"
    prompt = ("html outline", "o")
    content_types = ["text/html"]

    def __call__(self, data, **metadata):
        data = data.decode("utf-8", "replace")
        h = html2text.HTML2Text(baseurl="")
        h.ignore_images = True
        h.body_width = 0
        outline = h.handle(data)
        return "HTML Outline", format_text(outline)
