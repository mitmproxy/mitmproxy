import { RequestPanel } from "@/components/flow-view/request-panel";
import { HttpBar } from "./http-message/http-bar";
import { ResponsePanel } from "./response-panel";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { useAppSelector } from "web/ducks/hooks";
import { tabsForFlowNext } from "web/ducks/ui/utils";
import { WithKeyboardNavigation } from "@/components/keyboard-navigation";

export function FlowView() {
  const flow = useAppSelector((state) => state.flows.selected[0]);
  let activeTabRequest = useAppSelector((state) => state.ui.flow.tabRequest);
  let activeTabResponse = useAppSelector((state) => state.ui.flow.tabResponse);

  const tabs = tabsForFlowNext(flow);

  // Set default response tab.
  if (tabs.response.indexOf(activeTabResponse) < 0) {
    if (activeTabResponse === "response" && flow.error) {
      activeTabResponse = "error";
    } else if (activeTabResponse === "error" && "response" in flow) {
      activeTabResponse = "response";
    } else {
      activeTabResponse = tabs.response[0];
    }
  }

  // Set default request tab.
  if (!activeTabRequest || tabs.request.indexOf(activeTabRequest) < 0) {
    activeTabRequest = tabs.request[0];
  }

  return (
    <div className="flex h-full flex-col">
      <div className="bg-muted/30 border-b px-4 py-3">
        {flow.type === "http" && <HttpBar flow={flow} />}
      </div>

      <WithKeyboardNavigation
        includeKeys={["ArrowUp", "ArrowDown"]}
        className="min-h-0"
      >
        <ResizablePanelGroup id="flow-view-panel-group" direction="horizontal">
          <ResizablePanel id="request-details-panel" defaultSize={50}>
            <RequestPanel tab={activeTabRequest} />
          </ResizablePanel>

          <ResizableHandle withHandle />

          <ResizablePanel id="response-details-panel" defaultSize={50}>
            <ResponsePanel tab={activeTabResponse} />
          </ResizablePanel>
        </ResizablePanelGroup>
      </WithKeyboardNavigation>
    </div>
  );
}
