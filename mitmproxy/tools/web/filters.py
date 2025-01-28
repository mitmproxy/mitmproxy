from typing import List

from mitmproxy import flowfilter
from mitmproxy.addons import view


class FiltersManager:
    def __init__(self):
        self.filters: dict[str:str] = {}

    def update_filter(self, name: str, expression: str):
        self.filters[name] = expression
        if not expression:
            del self.filters[name]
        print(self.filters)

    def get_matching_flow_ids(self, name: str, view: view.View) -> List[str]:
        expr = self.filters.get(name)
        if not expr:
            return []

        match_expr = flowfilter.parse(expr)
        return [f.id for f in view if match_expr(f)]

