from jsonpath_ng import jsonpath, parse

REQUESTS_PATH = "log.entries[*].request"
RESPONSE_PATH = "log.entries[*].response"
WEBSOCKETS_PATH = "log.entries[*]._websocketMessages"

# do an all on the entries where they have a particular request url first
# for websockets, then take this filtered list, and gather messages
# URL filter does the all

class HarVerifications():
    def __init__(self, har):
        self.har = har

    def current_page_ref(self):
        self.get_path('$.log.pages[-1].pageref')

    # current, *, or filter
    def entries(self, base_path , opts):
        if opts['filter'] == 'current':
            subfilter = "[?(@.pageref = " + self.current_page_ref() + ")]"
        else:
            subfilter = opts['filter']

        json_path = base_path + subfilter
        jp = parse(json_path)      


    def present(self, path):
        return len(self.entries({})) > 0;

    def not_present(self, items, property, string_or_regexp):
        return len(self.entries({})) == 0;

    def less_than(self, items, property, val):
       return all([item[property] < val for item in items])

