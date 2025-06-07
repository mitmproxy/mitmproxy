import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { FlowTable } from "@/components/flow-table";
import { useAppSelector } from "web/ducks/hooks";
import { CaptureSetup } from "@/components/modes/capture-setup";
import { FlowView } from "@/components/flow-view";
import { WithKeyboardNavigation } from "@/components/keyboard-navigation";

export function MainView() {
  const hasOneFlowSelected = useAppSelector(
    (state) => state.flows.selected.length === 1,
  );
  const hasFlows = useAppSelector((state) => state.flows.list.length > 0);
  // const currentTab = useAppSelector((state) => state.ui.tabs.current); // TODO: implement tabs

  return hasFlows ? (
    <ResizablePanelGroup direction="vertical">
      <ResizablePanel id="flow-table-panel" defaultSize={60}>
        <WithKeyboardNavigation
          // Theses keys are A) difficult to implement with backwards compatibility for web in mind and B) conflicting with the builtin keyboard navigation in the tabs.
          // Turned off for now until we have a better solution.
          excludeKeys={["ArrowLeft", "ArrowRight", "Tab"]}
          className="h-full"
        >
          <FlowTable />
        </WithKeyboardNavigation>
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
