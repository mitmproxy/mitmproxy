import { ChevronDown, ChevronRight, Filter } from "lucide-react";
import { useState } from "react";
import { Badge } from "./ui/badge";

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
    <div className="border-b bg-muted/10">
      <div
        className="flex items-center px-4 py-2 cursor-pointer hover:bg-muted/20"
        onClick={() => setShowFilterPanel(!showFilterPanel)}
      >
        {showFilterPanel ? (
          <ChevronDown className="w-4 h-4 mr-2" />
        ) : (
          <ChevronRight className="w-4 h-4 mr-2" />
        )}
        <Filter className="w-4 h-4 mr-2" />
        <span className="text-sm font-medium">Filter Settings</span>
      </div>

      {showFilterPanel && (
        <div className="px-4 pb-3 grid grid-cols-3 gap-3">
          <div>
            <p className="text-xs font-medium mb-2">Method</p>
            <div className="flex flex-wrap gap-1">
              <Badge
                variant={activeFilters.all ? "default" : "outline"}
                className="text-xs cursor-pointer"
                onClick={() => handleFilterClick("all")}
              >
                ALL
              </Badge>
              <Badge
                variant={activeFilters.get ? "default" : "outline"}
                className="text-xs cursor-pointer"
                onClick={() => handleFilterClick("get")}
              >
                GET
              </Badge>
              <Badge
                variant={activeFilters.post ? "default" : "outline"}
                className="text-xs cursor-pointer"
                onClick={() => handleFilterClick("post")}
              >
                POST
              </Badge>
              <Badge
                variant={activeFilters.put ? "default" : "outline"}
                className="text-xs cursor-pointer"
                onClick={() => handleFilterClick("put")}
              >
                PUT
              </Badge>
              <Badge
                variant={activeFilters.delete ? "default" : "outline"}
                className="text-xs cursor-pointer"
                onClick={() => handleFilterClick("delete")}
              >
                DELETE
              </Badge>
            </div>
          </div>

          <div>
            <p className="text-xs font-medium mb-2">Status</p>
            <div className="flex flex-wrap gap-1">
              <Badge
                variant={activeFilters["1xx"] ? "default" : "outline"}
                className="text-xs cursor-pointer"
                onClick={() => handleFilterClick("1xx")}
              >
                1xx
              </Badge>
              <Badge
                variant={activeFilters["2xx"] ? "default" : "outline"}
                className="text-xs cursor-pointer"
                onClick={() => handleFilterClick("2xx")}
              >
                2xx
              </Badge>
              <Badge
                variant={activeFilters["3xx"] ? "default" : "outline"}
                className="text-xs cursor-pointer"
                onClick={() => handleFilterClick("3xx")}
              >
                3xx
              </Badge>
              <Badge
                variant={activeFilters["4xx"] ? "default" : "outline"}
                className="text-xs cursor-pointer"
                onClick={() => handleFilterClick("4xx")}
              >
                4xx
              </Badge>
              <Badge
                variant={activeFilters["5xx"] ? "default" : "outline"}
                className="text-xs cursor-pointer"
                onClick={() => handleFilterClick("5xx")}
              >
                5xx
              </Badge>
            </div>
          </div>

          <div>
            <p className="text-xs font-medium mb-2">Content Type</p>
            <div className="flex flex-wrap gap-1">
              <Badge
                variant={activeFilters.json ? "default" : "outline"}
                className="text-xs cursor-pointer"
                onClick={() => handleFilterClick("json")}
              >
                JSON
              </Badge>
              <Badge
                variant={activeFilters.html ? "default" : "outline"}
                className="text-xs cursor-pointer"
                onClick={() => handleFilterClick("html")}
              >
                HTML
              </Badge>
              <Badge
                variant={activeFilters.js ? "default" : "outline"}
                className="text-xs cursor-pointer"
                onClick={() => handleFilterClick("js")}
              >
                JS
              </Badge>
              <Badge
                variant={activeFilters.css ? "default" : "outline"}
                className="text-xs cursor-pointer"
                onClick={() => handleFilterClick("css")}
              >
                CSS
              </Badge>
              <Badge
                variant={activeFilters.graphql ? "default" : "outline"}
                className="text-xs cursor-pointer"
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
