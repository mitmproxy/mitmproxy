import os, sys
import countershape
from countershape import Page, Directory, PythonModule, markup
import countershape.template
sys.path.insert(0, "..")
from libmproxy import filt

MITMPROXY_SRC = "~/git/public/mitmproxy"

if ns.options.website:
    ns.title = countershape.template.Template(None, "<h1>@!this.title!@</h1>")
    this.layout = countershape.Layout("_websitelayout.html")
else:
    ns.title = countershape.template.Template(None, "<h1>@!this.title!@</h1>")
    this.layout = countershape.Layout("_layout.html")

this.markup = markup.Markdown()
ns.docMaintainer = "Aldo Cortesi"
ns.docMaintainerEmail = "aldo@corte.si"
ns.copyright = u"\u00a9 mitmproxy project, 2012"

ns.index = countershape.widgets.SiblingPageIndex('/index.html', divclass="pageindex")

def mpath(p):
    p = os.path.join(MITMPROXY_SRC, p)
    return os.path.expanduser(p)

ns.license = file(mpath("LICENSE")).read()
ns.index_contents = file(mpath("README.mkd")).read()



top = os.path.abspath(os.getcwd())
def example(s):
    d = file(mpath(s)).read()
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



pages = [
    Page("index.html", "docs"),
    Page("intro.html", "Introduction"),
    Page("mitmproxy.html", "mitmproxy"),
    Page("mitmdump.html", "mitmdump"),
    Page("clientreplay.html", "Client-side replay"),
    Page("serverreplay.html", "Server-side replay"),
    Page("sticky.html", "Sticky cookies and auth"),
    Page("reverseproxy.html", "Reverse proxy mode"),
    Page("anticache.html", "Anticache"),
    Page("filters.html", "Filter expressions"),
    Page("scripts.html", "Scripts"),
    Page("ssl.html", "SSL interception"),
    Directory("certinstall"),
    Page("library.html", "libmproxy: mitmproxy as a library"),
    Directory("tutorials"),
    Page("faq.html", "FAQ"),
    Page("admin.html", "Administrivia")
]
