import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { FilterPanel } from "@/components/filter-panel";
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
    <div className="flex-1">
      <FilterPanel />

      <ResizablePanelGroup direction="vertical">
        <ResizablePanel defaultSize={60}>
          <div className="flex h-full flex-col">
            <div className="flex-1 overflow-hidden">
              <div className="h-full overflow-auto text-xs">
                <FlowTable />
              </div>
            </div>
          </div>
        </ResizablePanel>

        {hasOneFlowSelected && (
          <>
            <ResizableHandle />
            <FlowView />
          </>
        )}
      </ResizablePanelGroup>
    </div>
  ) : (
    <CaptureSetup />
  );
}
