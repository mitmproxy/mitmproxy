import { LuChevronDown, LuChevronRight, LuFilter } from "react-icons/lu";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";

export function FilterPanel() {
  const [activeFilters, setActiveFilters] = useState<{
    [key: string]: boolean;
  }>({
    all: true,
    http: false,
    https: false,
    websocket: false,
    json: false,
    html: false,
    form: false,
    xml: false,
    js: false,
    css: false,
    graphql: false,
    document: false,
    media: false,
    other: false,
    "1xx": false,
    "2xx": false,
    "3xx": false,
    "4xx": false,
    "5xx": false,
    get: false,
    post: false,
    put: false,
    delete: false,
  });
  const [showFilterPanel, setShowFilterPanel] = useState(true);

  const handleFilterClick = (filter: string) => {
    if (filter === "all") {
      setActiveFilters({
        all: true,
        http: false,
        https: false,
        websocket: false,
        json: false,
        html: false,
        form: false,
        xml: false,
        js: false,
        css: false,
        graphql: false,
        document: false,
        media: false,
        other: false,
        "1xx": false,
        "2xx": false,
        "3xx": false,
        "4xx": false,
        "5xx": false,
        get: false,
        post: false,
        put: false,
        delete: false,
      });
    } else {
      setActiveFilters((prev) => ({
        ...prev,
        [filter]: !prev[filter],
        all: false,
      }));
    }
  };

  return (
    <div className="bg-muted/10 border-b">
      <div
        className="hover:bg-muted/20 flex cursor-pointer items-center px-4 py-2"
        onClick={() => setShowFilterPanel(!showFilterPanel)}
      >
        {showFilterPanel ? (
          <LuChevronDown className="mr-2 h-4 w-4" />
        ) : (
          <LuChevronRight className="mr-2 h-4 w-4" />
        )}
        <LuFilter className="mr-2 h-4 w-4" />
        <span className="text-sm font-medium">Filter Settings</span>
      </div>

      {showFilterPanel && (
        <div className="grid grid-cols-3 gap-3 px-4 pb-3">
          <div>
            <p className="mb-2 text-xs font-medium">Method</p>
            <div className="flex flex-wrap gap-1">
              <Badge
                variant={activeFilters.all ? "default" : "outline"}
                className="cursor-pointer text-xs"
                onClick={() => handleFilterClick("all")}
              >
                ALL
              </Badge>
              <Badge
                variant={activeFilters.get ? "default" : "outline"}
                className="cursor-pointer text-xs"
                onClick={() => handleFilterClick("get")}
              >
                GET
              </Badge>
              <Badge
                variant={activeFilters.post ? "default" : "outline"}
                className="cursor-pointer text-xs"
                onClick={() => handleFilterClick("post")}
              >
                POST
              </Badge>
              <Badge
                variant={activeFilters.put ? "default" : "outline"}
                className="cursor-pointer text-xs"
                onClick={() => handleFilterClick("put")}
              >
                PUT
              </Badge>
              <Badge
                variant={activeFilters.delete ? "default" : "outline"}
                className="cursor-pointer text-xs"
                onClick={() => handleFilterClick("delete")}
              >
                DELETE
              </Badge>
            </div>
          </div>

          <div>
            <p className="mb-2 text-xs font-medium">Status</p>
            <div className="flex flex-wrap gap-1">
              <Badge
                variant={activeFilters["1xx"] ? "default" : "outline"}
                className="cursor-pointer text-xs"
                onClick={() => handleFilterClick("1xx")}
              >
                1xx
              </Badge>
              <Badge
                variant={activeFilters["2xx"] ? "default" : "outline"}
                className="cursor-pointer text-xs"
                onClick={() => handleFilterClick("2xx")}
              >
                2xx
              </Badge>
              <Badge
                variant={activeFilters["3xx"] ? "default" : "outline"}
                className="cursor-pointer text-xs"
                onClick={() => handleFilterClick("3xx")}
              >
                3xx
              </Badge>
              <Badge
                variant={activeFilters["4xx"] ? "default" : "outline"}
                className="cursor-pointer text-xs"
                onClick={() => handleFilterClick("4xx")}
              >
                4xx
              </Badge>
              <Badge
                variant={activeFilters["5xx"] ? "default" : "outline"}
                className="cursor-pointer text-xs"
                onClick={() => handleFilterClick("5xx")}
              >
                5xx
              </Badge>
            </div>
          </div>

          <div>
            <p className="mb-2 text-xs font-medium">Content Type</p>
            <div className="flex flex-wrap gap-1">
              <Badge
                variant={activeFilters.json ? "default" : "outline"}
                className="cursor-pointer text-xs"
                onClick={() => handleFilterClick("json")}
              >
                JSON
              </Badge>
              <Badge
                variant={activeFilters.html ? "default" : "outline"}
                className="cursor-pointer text-xs"
                onClick={() => handleFilterClick("html")}
              >
                HTML
              </Badge>
              <Badge
                variant={activeFilters.js ? "default" : "outline"}
                className="cursor-pointer text-xs"
                onClick={() => handleFilterClick("js")}
              >
                JS
              </Badge>
              <Badge
                variant={activeFilters.css ? "default" : "outline"}
                className="cursor-pointer text-xs"
                onClick={() => handleFilterClick("css")}
              >
                CSS
              </Badge>
              <Badge
                variant={activeFilters.graphql ? "default" : "outline"}
                className="cursor-pointer text-xs"
                onClick={() => handleFilterClick("graphql")}
              >
                GraphQL
              </Badge>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
