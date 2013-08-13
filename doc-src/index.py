import os, sys
import countershape
from countershape import Page, Directory, PythonModule, markup, model
import countershape.template
sys.path.insert(0, "..")
from libmproxy import filt

MITMPROXY_SRC = "~/mitmproxy/mitmproxy"

if ns.options.website:
    ns.idxpath = "doc/index.html"
    this.layout = countershape.Layout("_websitelayout.html")
else:
    ns.idxpath = "index.html"
    this.layout = countershape.Layout("_layout.html")


ns.title = countershape.template.Template(None, "<h1>@!this.title!@</h1>")
this.titlePrefix = "mitmproxy 0.9 - "
this.markup = markup.Markdown(extras=["footnotes"])

ns.docMaintainer = "Aldo Cortesi"
ns.docMaintainerEmail = "aldo@corte.si"
ns.copyright = u"\u00a9 mitmproxy project, 2013"

def mpath(p):
    p = os.path.join(MITMPROXY_SRC, p)
    return os.path.expanduser(p)

ns.index_contents = file(mpath("README.mkd")).read()

def example(s):
    d = file(mpath(s)).read().rstrip()
    extemp = """<div class="example">%s<div class="example_legend">(%s)</div></div>"""
    return extemp%(countershape.template.Syntax("py")(d), s)
ns.example = example


filt_help = []
for i in filt.filt_unary:
    filt_help.append(
        ("~%s"%i.code, i.help)
    )
for i in filt.filt_rex:
    filt_help.append(
        ("~%s regex"%i.code, i.help)
    )
for i in filt.filt_int:
    filt_help.append(
        ("~%s int"%i.code, i.help)
    )
filt_help.sort()
filt_help.extend(
    [
        ("!", "unary not"),
        ("&", "and"),
        ("|", "or"),
        ("(...)", "grouping"),
    ]
)
ns.filt_help = filt_help


def nav(page, current, state):
    if current.match(page, False):
        pre = '<li class="active">'
    else:
        pre = "<li>"
    p = state.application.getPage(page)
    return pre + '<a href="%s">%s</a></li>'%(model.UrlTo(page), p.title)
ns.nav = nav

pages = [
    Page("index.html", "Introduction"),
    Page("install.html", "Installation"),
    Page("mitmproxy.html", "mitmproxy"),
    Page("mitmdump.html", "mitmdump"),
    Page("howmitmproxy.html", "How mitmproxy works"),

    Page("ssl.html", "Overview"),
    Directory("certinstall"),
    Directory("scripting"),
    Directory("tutorials"),
    Page("transparent.html", "Overview"),
    Directory("transparent"),
]
