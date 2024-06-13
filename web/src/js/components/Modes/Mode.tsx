import * as React from "react";
import { ModeToggle } from "../common/MenuToggle";

export enum ModeType {
    REGULAR = "regular",
    LOCAL = "local",
    WIREGUARD = "wireguard",
    REVERSE = "reverse",
}

export interface ModeProps {
    title: string;
    description: string;
    children?: React.ReactNode;
    type: ModeType;
}

export default function Mode(props: ModeProps) {
    return (
        <div>
            <h4 className="mode-title">{props.title}</h4>
            <p className="mode-description">{props.description}</p>
            <ModeToggle modeType={props.type}>{props.children}</ModeToggle>
        </div>
    );
}
