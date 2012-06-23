from countershape import widgets, layout, html, blog, markup, sitemap
from countershape.doc import *

ns.foot = "Copyright 2012 Aldo Cortesi"
this.markup = markup.Markdown(extras=dict(footnotes=True))
this.layout = layout.FileLayout("_layout_full.html")
this.titlePrefix = ""
this.site_url = "http://corte.si"
pages = [
    Page("index.html", "overview", namespace=dict(section="index")),
    Page("pathod.html", "pathod", namespace=dict(section="docs")),
    Page("pathoc.html", "pathoc", namespace=dict(section="docs")),
    Page("test.html", "libpathod.test", namespace=dict(section="docs")),
    sitemap.Sitemap("sitemap.xml")
]
