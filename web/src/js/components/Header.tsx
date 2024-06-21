import React, { useEffect, useState } from "react";
import classnames from "classnames";
import FileMenu from "./Header/FileMenu";
import ConnectionIndicator from "./Header/ConnectionIndicator";
import HideInStatic from "./common/HideInStatic";
import CaptureMenu from "./Header/CaptureMenu";
import { useAppSelector } from "../ducks";
import StartMenu from "./Header/StartMenu";
import OptionMenu from "./Header/OptionMenu";
import FlowMenu from "./Header/FlowMenu";
import { Menu } from "./ProxyApp";
import { shallowEqual } from "react-redux";

interface HeaderProps {
    ActiveMenu: Menu;
    setActiveMenu: React.Dispatch<Menu>;
}

export default function Header({ ActiveMenu, setActiveMenu }: HeaderProps) {
    const selectedFlows = useAppSelector(
            (state) =>
                state.flows.selected.filter((id) => id in state.flows.byId),
            shallowEqual,
        ),
        [wasFlowSelected, setWasFlowSelected] = useState(false);

    let entries: Menu[] = [CaptureMenu, StartMenu, OptionMenu];
    if (selectedFlows.length > 0) {
        entries.push(FlowMenu);
    }

    useEffect(() => {
        if (selectedFlows.length > 0 && !wasFlowSelected) {
            setActiveMenu(FlowMenu);
            setWasFlowSelected(true);
        } else if (selectedFlows.length === 0) {
            if (wasFlowSelected) {
                setWasFlowSelected(false);
            }
            if (ActiveMenu === FlowMenu) {
                setActiveMenu(StartMenu);
            }
        }
    }, [selectedFlows, wasFlowSelected, ActiveMenu, setActiveMenu]);

    function handleClick(active: Menu, e: React.MouseEvent<HTMLAnchorElement>) {
        e.preventDefault();
        setActiveMenu(active);
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
