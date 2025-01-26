from typing import List
from mitmproxy.tools.cmdline import mitmproxy
from mitmproxy import flowfilter


class FiltersManager():
       
    def __init__(self, view):
        self.filters: dict[str, flowfilter.TFilter] = {
            "search": flowfilter.match_all,
            "highlight": flowfilter.match_all,
        }
        self.view = view

    def update_filter(self, name: str, expression: flowfilter.TFilter):
        self.filters[name] = expression

    def get_filter(self, name: str) -> flowfilter.TFilter:
        return self.filters.get(name, flowfilter.match_all)
    
    def get_all_filters(self) -> dict[str, flowfilter.TFilter]:
        return self.filters.copy()

    def get_matching_flow_ids(self) -> List[str]:
        match_search = flowfilter.parse(self.get_filter("search")) # TODO: handle highlight
        return [f.id for f in self.view if match_search(f)]