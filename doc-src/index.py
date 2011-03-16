import os
import countershape
from countershape import Page, Directory, PythonModule, markup
import countershape.grok, countershape.template    

this.layout = countershape.Layout("_layout.html")
ns.docTitle = "mitmproxy"
this.markup = markup.Markdown()
ns.docMaintainer = "Aldo Cortesi"
ns.docMaintainerEmail = "aldo@corte.si"
ns.copyright = u"\u00a9 mitmproxy project, 2011"
ns.title = countershape.template.Template(None, "<h1> @!docTitle!@ - @!this.title!@ </h1>")

ns.index = countershape.widgets.SiblingPageIndex('/index.html', divclass="pageindex")

ns.license = file("../LICENSE").read()
ns.index_contents = file("../README.mkd").read()


top = os.path.abspath(os.getcwd())
def example(s):
    d = file(os.path.join(top, s)).read()
    return countershape.template.pySyntax(d)


ns.example = example



pages = [
    Page("index.html", "Index"),
    Page("intro.html", "Introduction"),
    Page("clientreplay.html", "Client-side replay"),
    Page("serverreplay.html", "Server-side replay"),
    Page("scripts.html", "External scripts"),
    Page("library.html", "libmproxy: mitmproxy as a library"),
    Page("ssl.html", "SSL"),
    Page("faq.html", "FAQ"),
    Page("admin.html", "Administrivia")
]
