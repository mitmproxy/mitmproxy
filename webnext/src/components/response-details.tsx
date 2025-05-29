import { ScrollArea } from "./ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";

const mockResponseData = {
  data: {
    trendingTopics: [
      {
        id: "268",
        name: "Artificial Intelligence",
        slug: "artificial-intelligence",
        __typename: "Topic",
      },
      {
        id: "46",
        name: "Productivity",
        slug: "productivity",
        __typename: "Topic",
      },
      {
        id: "237",
        name: "SaaS",
        slug: "saas",
        __typename: "Topic",
      },
      {
        id: "164",
        name: "Marketing",
        slug: "marketing",
        __typename: "Topic",
      },
    ],
  },
};

export function ResponseDetails() {
  return (
    <Tabs defaultValue="body" className="h-full flex flex-col">
      <div className="border-b px-4 py-2 bg-muted/20">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm font-medium">Response</span>
          <span className="text-xs text-muted-foreground">JSON</span>
        </div>
        <TabsList className="grid w-full grid-cols-5 h-8">
          <TabsTrigger value="header" className="text-xs">
            Header
          </TabsTrigger>
          <TabsTrigger value="body" className="text-xs">
            Body
          </TabsTrigger>
          <TabsTrigger value="set-cookie" className="text-xs">
            Set-Cookie
          </TabsTrigger>
          <TabsTrigger value="raw" className="text-xs">
            Raw
          </TabsTrigger>
          <TabsTrigger value="treeview" className="text-xs">
            Treeview
          </TabsTrigger>
        </TabsList>
      </div>

      <TabsContent value="body" className="flex-1 p-0">
        <ScrollArea className="h-full">
          <div className="relative">
            <div className="absolute left-0 top-0 bottom-0 w-12 bg-muted/50 border-r flex flex-col text-xs text-muted-foreground">
              {Array.from({ length: 25 }, (_, i) => (
                <div key={i + 1} className="px-2 py-0.5 text-right">
                  {i + 1}
                </div>
              ))}
            </div>
            <pre className="pl-14 p-4 text-xs font-mono">
              {JSON.stringify(mockResponseData, null, 2)}
            </pre>
          </div>
        </ScrollArea>
      </TabsContent>

      <TabsContent value="header" className="flex-1 p-4">
        <div className="space-y-2">
          <div className="flex">
            <div className="w-32 text-xs font-medium text-muted-foreground">
              Content-Type
            </div>
            <div className="text-xs font-mono">application/json</div>
          </div>
          <div className="flex">
            <div className="w-32 text-xs font-medium text-muted-foreground">
              Cache-Control
            </div>
            <div className="text-xs font-mono">no-cache</div>
          </div>
          <div className="flex">
            <div className="w-32 text-xs font-medium text-muted-foreground">
              Server
            </div>
            <div className="text-xs font-mono">nginx/1.18.0</div>
          </div>
        </div>
      </TabsContent>
    </Tabs>
  );
}
