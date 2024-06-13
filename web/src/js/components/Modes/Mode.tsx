import * as React from "react";
import { ModeToggle } from "../common/MenuToggle";

export interface ModeProps {
    title: string;
    description: string;
    children?: React.ReactNode;
}

export default function Mode(props: ModeProps) {
    return (
        <div>
            <h4 className="mode-title">{props.title}</h4>
            <p className="mode-description">
                {props.description}
            </p>
            <ModeToggle>{props.children}</ModeToggle>
        </div>
    );
}
