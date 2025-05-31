import { ResponseHeadersTable } from "@/components/flow-view/http-message/headers-table";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export type ResponseDetailsProps = {
  tab: string;
};

export function ResponseDetails({ tab = "headers" }: ResponseDetailsProps) {
  return (
    <Tabs defaultValue={tab} className="h-full p-4">
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

      <TabsContent value="headers" className="min-h-0">
        <ScrollArea className="h-full">
          <ResponseHeadersTable />
        </ScrollArea>
      </TabsContent>
    </Tabs>
  );
}
