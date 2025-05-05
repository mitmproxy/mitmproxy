import React, { useEffect, useState } from "react";
import classnames from "classnames";
import FileMenu from "./Header/FileMenu";
import ConnectionIndicator from "./Header/ConnectionIndicator";
import HideInStatic from "./common/HideInStatic";
import CaptureMenu from "./Header/CaptureMenu";
import { useAppDispatch, useAppSelector } from "../ducks";
import FlowListMenu from "./Header/FlowListMenu";
import OptionMenu from "./Header/OptionMenu";
import FlowMenu from "./Header/FlowMenu";
import { Menu } from "./ProxyApp";
import { Tab, setCurrent } from "../ducks/ui/tabs";

const tabs: { [key in Tab]: Menu } = {
    [Tab.Capture]: CaptureMenu,
    [Tab.FlowList]: FlowListMenu,
    [Tab.Options]: OptionMenu,
    [Tab.Flow]: FlowMenu,
};

export default function Header() {
    const dispatch = useAppDispatch();
    const currentTab = useAppSelector((state) => state.ui.tabs.current);
    const selectedFlows = useAppSelector((state) => state.flows.selected);
    const [wasFlowSelected, setWasFlowSelected] = useState(false);

    const entries: Tab[] = [Tab.Capture, Tab.FlowList, Tab.Options];
    if (selectedFlows.length > 0) {
        entries.push(Tab.Flow);
    }

    // Switch to "Flow" tab if we just selected a new flow.
    useEffect(() => {
        if (selectedFlows.length > 0 && !wasFlowSelected) {
            // User just clicked on a flow without having previously selected one.
            dispatch(setCurrent(Tab.Flow));
            setWasFlowSelected(true);
        } else if (selectedFlows.length === 0) {
            if (wasFlowSelected) {
                setWasFlowSelected(false);
            }
            if (currentTab === Tab.Flow) {
                dispatch(setCurrent(Tab.FlowList));
            }
        }
    }, [selectedFlows, wasFlowSelected, currentTab]);

    function handleClick(tab: Tab, e: React.MouseEvent<HTMLAnchorElement>) {
        e.preventDefault();
        dispatch(setCurrent(tab));
    }

    const ActiveMenu = tabs[currentTab];

    return (
        <header>
            <nav className="nav-tabs nav-tabs-lg">
                <FileMenu />
                {entries.map((tab) => (
                    <a
                        key={tab}
                        href="#"
                        className={classnames({ active: tab === currentTab })}
                        onClick={(e) => handleClick(tab, e)}
                    >
                        {tabs[tab].title}
                    </a>
                ))}
                <HideInStatic>
                    <ConnectionIndicator />
                </HideInStatic>
            </nav>
            <div>
                <ActiveMenu />
            </div>
        </header>
    );
}
