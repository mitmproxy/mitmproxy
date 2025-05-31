import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

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

export type ResponseDetailsProps = {
  tab: string;
};

export function ResponseDetails({ tab = "headers" }: ResponseDetailsProps) {
  return (
    <Tabs defaultValue={tab} className="flex h-full flex-col">
      <div className="bg-muted/20 border-b px-4 py-2">
        <div className="mb-2 flex items-center gap-2">
          <span className="text-sm font-medium">Response</span>
          <span className="text-muted-foreground text-xs">JSON</span>
        </div>
        <TabsList className="grid h-8 w-full grid-cols-5">
          <TabsTrigger value="headers" className="text-xs">
            Headers
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
            <div className="bg-muted/50 text-muted-foreground absolute top-0 bottom-0 left-0 flex w-12 flex-col border-r text-xs">
              {Array.from({ length: 25 }, (_, i) => (
                <div key={i + 1} className="px-2 py-0.5 text-right">
                  {i + 1}
                </div>
              ))}
            </div>
            <pre className="p-4 pl-14 font-mono text-xs">
              {JSON.stringify(mockResponseData, null, 2)}
            </pre>
          </div>
        </ScrollArea>
      </TabsContent>

      <TabsContent value="header" className="flex-1 p-4">
        <div className="space-y-2">
          <div className="flex">
            <div className="text-muted-foreground w-32 text-xs font-medium">
              Content-Type
            </div>
            <div className="font-mono text-xs">application/json</div>
          </div>
          <div className="flex">
            <div className="text-muted-foreground w-32 text-xs font-medium">
              Cache-Control
            </div>
            <div className="font-mono text-xs">no-cache</div>
          </div>
          <div className="flex">
            <div className="text-muted-foreground w-32 text-xs font-medium">
              Server
            </div>
            <div className="font-mono text-xs">nginx/1.18.0</div>
          </div>
        </div>
      </TabsContent>
    </Tabs>
  );
}
