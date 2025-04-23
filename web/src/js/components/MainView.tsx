import * as React from "react";
import Splitter from "./common/Splitter";
import FlowTable from "./FlowTable";
import FlowView from "./FlowView";
import { useAppSelector } from "../ducks";
import CaptureSetup from "./Modes/CaptureSetup";
import Modes from "./Modes";
import { Tab } from "../ducks/ui/tabs";

export default function MainView() {
    const hasOneFlowSelected = useAppSelector(
        (state) => state.flows.selected.length === 1,
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
                    {hasOneFlowSelected && (
                        <>
                            <Splitter key="splitter" />
                            <FlowView key="flowDetails" />
                        </>
                    )}
                </>
            )}
        </div>
    );
}
