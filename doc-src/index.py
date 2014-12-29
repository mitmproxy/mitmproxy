import os
import sys
import datetime
import countershape
from countershape import Page, Directory, markup, model
import countershape.template

MITMPROXY_SRC = os.path.abspath(
    os.path.expanduser(os.environ.get("MITMPROXY_SRC", ".."))
)
sys.path.insert(0, MITMPROXY_SRC)
from libmproxy import filt, version

ns.VERSION = version.VERSION

if ns.options.website:
    ns.idxpath = "doc/index.html"
    this.layout = countershape.Layout("_websitelayout.html")
else:
    ns.idxpath = "index.html"
    this.layout = countershape.Layout("_layout.html")

ns.title = countershape.template.Template(None, "<h1>@!this.title!@</h1>")
this.titlePrefix = "%s - " % version.NAMEVERSION
this.markup = markup.Markdown(extras=["footnotes"])

ns.docMaintainer = "Aldo Cortesi"
ns.docMaintainerEmail = "aldo@corte.si"
ns.copyright = u"\u00a9 mitmproxy project, %s" % datetime.date.today().year


def mpath(p):
    p = os.path.join(MITMPROXY_SRC, p)
    return os.path.expanduser(p)


def example(s):
    d = file(mpath(s)).read().rstrip()
    extemp = """<div class="example">%s<div class="example_legend">(%s)</div></div>"""
    return extemp%(countershape.template.Syntax("py")(d), s)


ns.example = example


ns.filt_help = filt.help


def nav(page, current, state):
    if current.match(page, False):
        pre = '<li class="active">'
    else:
        pre = "<li>"
    p = state.application.getPage(page)
    return pre + '<a href="%s">%s</a></li>'%(model.UrlTo(page), p.title)
ns.nav = nav
ns.navbar = countershape.template.File(None, "_nav.html")


pages = [
    Page("index.html", "Introduction"),
    Page("install.html", "Installation"),
    Page("howmitmproxy.html", "How mitmproxy works"),
    Page("modes.html", "Modes of Operation"),

    Page("mitmproxy.html", "mitmproxy"),
    Page("mitmdump.html", "mitmdump"),
    Page("config.html", "configuration"),

    Page("ssl.html", "Overview"),
    Directory("certinstall"),
    Directory("scripting"),
    Directory("tutorials"),
    Page("transparent.html", "Overview"),
    Directory("transparent"),
]
