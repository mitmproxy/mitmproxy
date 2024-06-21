import * as React from "react";
import Splitter from "./common/Splitter";
import FlowTable from "./FlowTable";
import FlowView from "./FlowView";
import { useAppSelector } from "../ducks";
import CaptureSetup from "./CaptureSetup";
import CaptureMenu from "./Header/CaptureMenu";
import { Menu } from "./ProxyApp";
import Modes from "./Modes";

interface MainViewProps {
    ActiveMenu: Menu;
}

export default function MainView({ ActiveMenu }: MainViewProps) {
    const hasSelection = useAppSelector(
        (state) => !!state.flows.byId[state.flows.selected[0]],
    );
    const hasFlows = useAppSelector((state) => state.flows.list.length > 0);

    return (
        <div className="main-view">
            {ActiveMenu === CaptureMenu ? (
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
