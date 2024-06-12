import * as React from "react";

export interface ModeProps {
    title: string;
    description: string;
    children?: React.ReactNode;
}

export default function Mode(props: ModeProps) {
    return (
        <div>
            <h4 style={{ fontWeight: 600 }}>{props.title}</h4>
            <p style={{ color: "#B2B2B2", marginTop: -10 }}>
                {props.description}
            </p>
            {props.children}
        </div>
    );
}
