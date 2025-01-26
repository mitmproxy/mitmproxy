from typing import List
from mitmproxy.tools.cmdline import mitmproxy
from mitmproxy import flowfilter


class FiltersManager():
       
    def __init__(self, view):
        self.filters: dict[str, flowfilter.TFilter] = {
            "search": "",
            "highlight": "",
        }
        self.view = view

    def update_filter(self, name: str, expression: flowfilter.TFilter):
        self.filters[name] = expression

    def get_filter(self, name: str) -> flowfilter.TFilter:
        return self.filters.get(name, "")
    
    def get_all_filters(self) -> dict[str, flowfilter.TFilter]:
        return self.filters.copy()

    def get_matching_flow_ids(self) -> List[str]:
        search = self.get_filter("search")
        highlight = self.get_filter("highlight")
        if search and highlight:
            match_search = flowfilter.parse(search)
            match_highlight = flowfilter.parse(highlight)
            return [f.id for f in self.view if match_search(f) and match_highlight(f)]
        elif search:
            match_search = flowfilter.parse(search)
            return [f.id for f in self.view if match_search(f)]
        elif highlight:
            match_highlight = flowfilter.parse(highlight)
            return [f.id for f in self.view if match_highlight(f)]
        else:
            return []