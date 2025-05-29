import { ScrollArea } from "./ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";

const mockRequestDetails = {
  headers: {
    Host: "www.producthunt.com",
    Connection: "keep-alive",
    "Content-Length": "186",
    "sec-ch-ua":
      '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
    accept: "*/*",
    "content-type": "application/json",
    "x-requested-with": "XMLHttpRequest",
    "sec-ch-ua-mobile": "?0",
    "User-Agent":
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "sec-ch-ua-platform": '"macOS"',
    Origin: "https://www.producthunt.com",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    Referer: "https://www.producthunt.com/",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    Cookie:
      "_delighted_web=%7B%22kxmx4D4TpGnYW%22%3A%7B%22_delighted_fwYs2Z%22%3A%22value%22%7D%7D",
  },
};
export function RequestDetails() {
  return (
    <Tabs defaultValue="header" className="flex h-full flex-col">
      <div className="bg-muted/20 border-b px-4 py-2">
        <div className="mb-2 flex items-center gap-2">
          <span className="text-sm font-medium">Request</span>
        </div>
        <TabsList className="grid h-8 w-full grid-cols-6">
          <TabsTrigger value="header" className="text-xs">
            Header
          </TabsTrigger>
          <TabsTrigger value="query" className="text-xs">
            Query
          </TabsTrigger>
          <TabsTrigger value="body" className="text-xs">
            Body
          </TabsTrigger>
          <TabsTrigger value="cookies" className="text-xs">
            Cookies
          </TabsTrigger>
          <TabsTrigger value="raw" className="text-xs">
            Raw
          </TabsTrigger>
          <TabsTrigger value="summary" className="text-xs">
            Summary
          </TabsTrigger>
        </TabsList>
      </div>

      <TabsContent value="header" className="flex-1 p-0">
        <ScrollArea className="h-full">
          <div className="space-y-2 p-4">
            {Object.entries(mockRequestDetails.headers).map(([key, value]) => (
              <div key={key} className="flex">
                <div className="text-muted-foreground w-32 flex-shrink-0 text-xs font-medium">
                  {key}
                </div>
                <div className="font-mono text-xs break-all">{value}</div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </TabsContent>

      <TabsContent value="body" className="flex-1 p-4">
        <pre className="bg-muted/50 rounded p-3 font-mono text-xs">
          {`{
  "query": "query TrendingTopics { trendingTopics { id name slug __typename } }"
}`}
        </pre>
      </TabsContent>
    </Tabs>
  );
}
