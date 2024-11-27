import * as React from "react";
import Splitter from "./common/Splitter";
import FlowTable from "./FlowTable";
import FlowView from "./FlowView";
import { useAppSelector } from "../ducks";
import CaptureSetup from "./Modes/CaptureSetup";
import Modes from "./Modes";
import { Tab } from "../ducks/ui/tabs";

export default function MainView() {
    const hasSelection = useAppSelector(
        (state) => !!state.flows.byId[state.flows.selected[0]],
    );
    const hasFlows = useAppSelector((state) => state.flows.list.length > 0);
    const currentTab = useAppSelector((state) => state.ui.tabs.current);

    return (
        <div className="main-view">
            {currentTab === Tab.Capture ? (
                <Modes />
            ) : (
                <>
                    {hasFlows ? <FlowTable /> : <CaptureSetup />}
                    {hasSelection && <Splitter key="splitter" />}
                    {hasSelection && <FlowView key="flowDetails" />}
                </>
            )}
        </div>
    );
}
