import { HeadersTable } from "@/components/flow-view/http-message/headers-table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export type RequestDetailsProps = {
  tab: string;
};

export function RequestDetails({ tab = "headers" }: RequestDetailsProps) {
  return (
    <Tabs defaultValue={tab} className="p-4">
      <div className="mb-2 flex items-center gap-2">
        <span className="text-sm font-medium">Request</span>
      </div>
      <TabsList className="grid h-8 w-full grid-cols-6">
        <TabsTrigger value="headers" className="text-xs">
          Headers
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

      <TabsContent value="headers">
        <HeadersTable />
      </TabsContent>
    </Tabs>
  );
}
