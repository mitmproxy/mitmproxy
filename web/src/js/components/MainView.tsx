import * as React from "react";
import Splitter from "./common/Splitter";
import FlowTable from "./FlowTable";
import FlowView from "./FlowView";
import { useAppSelector } from "../ducks";
import CaptureSetup from "./CaptureSetup";
import FlowTreeView from "./FlowTreeView";
import FlowTreeView_2 from "./FlowTreeView_2";

export default function MainView() {
    const flows = useAppSelector((state) => state.flows.view);
    const highlight = useAppSelector((state) => state.flows.highlight);
    const selected = useAppSelector(
        (state) => state.flows.byId[state.flows.selected[0]]
    );
    const hasSelection = !!selected;

    const hasFlows = useAppSelector((state) => state.flows.list.length > 0);
    const isTreeView = useAppSelector((state) => state.ui.flow.isTreeView);

    return (
        <div className="main-view">
            {hasFlows ? (
                isTreeView ? (
                    <>
                        {/*<FlowTreeView flows={flows} highlight={highlight} />*/}
                        <FlowTreeView_2 flows={flows} highlight={highlight} />
                    </>
                ) : (
                    <FlowTable
                        flows={flows}
                        highlight={highlight}
                        selected={selected}
                    />
                )
            ) : (
                <CaptureSetup />
            )}

            {hasSelection && <Splitter key="splitter" />}
            {hasSelection && <FlowView key="flowDetails" />}
        </div>
    );
}
