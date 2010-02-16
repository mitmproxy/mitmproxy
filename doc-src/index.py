import countershape
from countershape import Page, Directory, PythonModule
import countershape.grok

this.layout = countershape.Layout("_layout.html")
this.markup = "markdown"
ns.docTitle = "mitmproxy"
ns.docMaintainer = "Aldo Cortesi"
ns.docMaintainerEmail = "aldo@corte.si"
ns.copyright = "Aldo Cortesi 2010"
ns.head = countershape.template.Template(None, "<h1> @!docTitle!@ - @!this.title!@ </h1>")
ns.sidebar = countershape.widgets.SiblingPageIndex(
            '/index.html',
            exclude=['countershape']
          )

ns.license = file("../LICENSE").read()
ns.index_contents = file("../README").read()
ns.example = file("../examples/stickycookies.py").read()

pages = [
    Page("index.html", "introduction"),
    Page("library.html", "library"),
    Page("faq.html", "faq"),
    Page("admin.html", "administrivia")
]
