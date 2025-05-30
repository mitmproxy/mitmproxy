import { RequestDetails } from "@/components/request-details";
import { ResponseDetails } from "@/components/response-details";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";

export function FlowView() {
  return (
    <ResizablePanel defaultSize={40}>
      {/*  <div className="bg-muted/30 border-b px-4 py-3">
            <div className="flex items-center gap-3">
              <Badge
                variant="outline"
                className="px-2 py-1 text-sm font-medium"
              >
                {selectedRequest.method}
              </Badge>
              <Badge
                variant="outline"
                className="bg-green-100 px-2 py-1 text-sm text-green-700 dark:bg-green-900/50 dark:text-green-300"
              >
                {selectedRequest.code} OK
              </Badge>
              <span className="font-mono text-sm text-blue-600 dark:text-blue-400">
                {selectedRequest.url}
              </span>
            </div>
          </div> */}

      <ResizablePanelGroup direction="horizontal">
        <ResizablePanel defaultSize={50}>
          <RequestDetails />
        </ResizablePanel>

        <ResizableHandle withHandle />

        <ResizablePanel defaultSize={50}>
          <ResponseDetails />
        </ResizablePanel>
      </ResizablePanelGroup>
    </ResizablePanel>
  );
}
