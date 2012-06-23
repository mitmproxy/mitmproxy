from countershape import widgets, layout, html, blog, markup, sitemap
from countershape.doc import *

ns.foot = "Copyright 2012 Aldo Cortesi"
this.markup = markup.Markdown(extras=dict(footnotes=True))
this.layout = layout.FileLayout("_layout_full.html")
this.titlePrefix = ""
this.site_url = "http://corte.si"
pages = [
    Page("index.html", "overview", namespace=dict(section="index")),
    Page("docs.html", "docs", namespace=dict(section="docs")),
    sitemap.Sitemap("sitemap.xml")
]
ns.sidebar = widgets.SiblingPageIndex(
                        pages[0],
                        depth=1,
                        divclass="sidebarmenu"
                    )
