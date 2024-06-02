import React, { useEffect, useState } from "react";
import classnames from "classnames";
import FileMenu from "./Header/FileMenu";
import ConnectionIndicator from "./Header/ConnectionIndicator";
import HideInStatic from "./common/HideInStatic";
import CaptureMenu from "./Header/CaptureMenu";
import { Menu, useTabMenuContext } from "../context/useTabMenuContext";
import { useAppSelector } from "../ducks";
import StartMenu from "./Header/StartMenu";
import OptionMenu from "./Header/OptionMenu";
import FlowMenu from "./Header/FlowMenu";

export default function Header() {
    const selectedFlows = useAppSelector((state) =>
        state.flows.selected.filter((id) => id in state.flows.byId)
    );
    const [wasFlowSelected, setWasFlowSelected] = useState(false);
    const { ActiveMenu, setActiveMenu } = useTabMenuContext();

    let entries: Menu[] = [CaptureMenu, StartMenu, OptionMenu];
    if (selectedFlows.length > 0) {
        entries.push(FlowMenu);
    }

    useEffect(() => {
        if (selectedFlows.length > 0 && !wasFlowSelected) {
            setActiveMenu(() => FlowMenu);
            setWasFlowSelected(true);
        } else if (selectedFlows.length === 0) {
            if (wasFlowSelected) {
                setWasFlowSelected(false);
            }
            if (ActiveMenu === FlowMenu) {
                setActiveMenu(() => StartMenu);
            }
        }
    }, [selectedFlows, wasFlowSelected, ActiveMenu, setActiveMenu]);

    function handleClick(active: Menu, e: React.MouseEvent<HTMLAnchorElement>) {
        e.preventDefault();
        setActiveMenu(() => active);
    }

    return (
        <header>
            <nav className="nav-tabs nav-tabs-lg">
                <FileMenu />
                {entries.map((Entry) => (
                    <a
                        key={Entry.title}
                        href="#"
                        className={classnames({ active: Entry === ActiveMenu })}
                        onClick={(e) => handleClick(Entry, e)}
                    >
                        {Entry.title}
                    </a>
                ))}
                <HideInStatic>
                    <ConnectionIndicator />
                </HideInStatic>
            </nav>
            <div
                className={classnames({
                    "empty-header": ActiveMenu === CaptureMenu,
                })}
            >
                <ActiveMenu />
            </div>
        </header>
    );
}
