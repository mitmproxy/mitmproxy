import string
import lxml.html
import lxml.etree
from mitmproxy import utils, contentviews


class ViewPigLatin(contentviews.View):
    name = "pig_latin_HTML"
    prompt = ("pig latin HTML", "l")
    content_types = ["text/html"]

    def __call__(self, data, **metadata):
        if utils.isXML(data):
            parser = lxml.etree.HTMLParser(
                strip_cdata=True,
                remove_blank_text=True
            )
            d = lxml.html.fromstring(data, parser=parser)
            docinfo = d.getroottree().docinfo

            def piglify(src):
                words = string.split(src)
                ret = ''
                for word in words:
                    idx = -1
                    while word[idx] in string.punctuation and (idx * -1) != len(word): idx -= 1
                    if word[0].lower() in 'aeiou':
                        if idx == -1:
                            ret += word[0:] + "hay"
                        else:
                            ret += word[0:len(word) + idx + 1] + "hay" + word[idx + 1:]
                    else:
                        if idx == -1:
                            ret += word[1:] + word[0] + "ay"
                        else:
                            ret += word[1:len(word) + idx + 1] + word[0] + "ay" + word[idx + 1:]
                    ret += ' '
                return ret.strip()

            def recurse(root):
                if hasattr(root, 'text') and root.text:
                    root.text = piglify(root.text)
                if hasattr(root, 'tail') and root.tail:
                    root.tail = piglify(root.tail)

                if len(root):
                    for child in root:
                        recurse(child)

            recurse(d)

            s = lxml.etree.tostring(
                d,
                pretty_print=True,
                doctype=docinfo.doctype
            )
            return "HTML", contentviews.format_text(s)


pig_view = ViewPigLatin()


def start(context, argv):
    context.add_contentview(pig_view)


def done(context):
    context.remove_contentview(pig_view)
