import os
import countershape
from countershape import Page, Directory, PythonModule, markup
import countershape.grok, countershape.template    

this.layout = countershape.Layout("_layout.html")
ns.docTitle = "mitmproxy"
this.markup = markup.Markdown()
ns.docMaintainer = "Aldo Cortesi"
ns.docMaintainerEmail = "aldo@corte.si"
ns.copyright = "Aldo Cortesi 2010"
ns.head = countershape.template.Template(None, "<h1> @!docTitle!@ - @!this.title!@ </h1>")
ns.sidebar = countershape.widgets.SiblingPageIndex(
            '/index.html',
            exclude=['countershape']
          )

ns.license = file("../LICENSE").read()
ns.index_contents = file("../README.mkd").read()


top = os.path.abspath(os.getcwd())
def example(s):
    d = file(os.path.join(top, s)).read()
    return countershape.template.pySyntax(d)


ns.example = example



pages = [
    Page("index.html", "introduction"),
    Page("mitmproxy.html", "mitmproxy"),
    Page("mitmdump.html", "mitmdump"),
    Page("scripts.html", "scripts"),
    Page("library.html", "libmproxy"),
    Page("faq.html", "faq"),
    Page("admin.html", "administrivia")
]
