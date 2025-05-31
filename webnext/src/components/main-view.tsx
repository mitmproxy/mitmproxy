import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { FlowTable } from "@/components/flow-table";
import { useAppSelector } from "web/ducks/hooks";
import { CaptureSetup } from "@/components/modes/capture-setup";
import { FlowView } from "@/components/flow-view";

export function MainView() {
  const hasOneFlowSelected = useAppSelector(
    (state) => state.flows.selected.length === 1,
  );
  const hasFlows = useAppSelector((state) => state.flows.list.length > 0);
  // const currentTab = useAppSelector((state) => state.ui.tabs.current); // TODO: implement tabs

  return hasFlows ? (
    <ResizablePanelGroup direction="vertical">
      <ResizablePanel id="flow-table-panel" defaultSize={60}>
        <FlowTable />
      </ResizablePanel>

      {hasOneFlowSelected && (
        <>
          <ResizableHandle />
          <ResizablePanel id="flow-view-panel" defaultSize={40}>
            <FlowView />
          </ResizablePanel>
        </>
      )}
    </ResizablePanelGroup>
  ) : (
    <CaptureSetup />
  );
}
