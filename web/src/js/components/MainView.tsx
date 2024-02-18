import * as React from "react";
import Splitter from "./common/Splitter";
import FlowTable from "./FlowTable";
import FlowView from "./FlowView";
import { useAppSelector } from "../ducks";
import CaptureSetup from "./CaptureSetup";
import FlowTreeView from "./FlowTreeView";

export default function MainView() {
    const hasSelection = useAppSelector(
        (state) => !!state.flows.byId[state.flows.selected[0]]
    );
    const hasFlows = useAppSelector((state) => state.flows.list.length > 0);
    const isTreeView = useAppSelector((state) => state.ui.flow.isTreeView);
    return (
        <div className="main-view">
            {hasFlows ? (
                isTreeView ? (
                    <FlowTreeView />
                ) : (
                    <FlowTable />
                )
            ) : (
                <CaptureSetup />
            )}

            {hasSelection && <Splitter key="splitter" />}
            {hasSelection && <FlowView key="flowDetails" />}
        </div>
    );
}
