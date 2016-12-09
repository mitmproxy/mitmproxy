import lxml.etree

from . import base


class ViewXML(base.View):
    name = "XML"
    prompt = ("xml", "x")
    content_types = ["text/xml"]

    def __call__(self, data, **metadata):
        parser = lxml.etree.XMLParser(
            remove_blank_text=True,
            resolve_entities=False,
            strip_cdata=False,
            recover=False
        )
        try:
            document = lxml.etree.fromstring(data, parser)
        except lxml.etree.XMLSyntaxError:
            return None
        docinfo = document.getroottree().docinfo

        prev = []
        p = document.getroottree().getroot().getprevious()
        while p is not None:
            prev.insert(
                0,
                lxml.etree.tostring(p)
            )
            p = p.getprevious()
        doctype = docinfo.doctype
        if prev:
            doctype += "\n".join(p.decode() for p in prev).strip()
        doctype = doctype.strip()

        s = lxml.etree.tostring(
            document,
            pretty_print=True,
            xml_declaration=True,
            doctype=doctype or None,
            encoding=docinfo.encoding
        )

        return "XML-like data", base.format_text(s)
