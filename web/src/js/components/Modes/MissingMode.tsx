import * as React from "react";

interface MissingModeProps {
    title: string;
    description: string;
}

export default function MissingMode({ title, description }: MissingModeProps) {
    return (
        <div className="missing-mode-container">
            <div className="title-icon-container">
                <h4 className="mode-title">{title}</h4>
                <i
                    className="fa fa-exclamation-triangle"
                    aria-hidden="true"
                ></i>
            </div>
            <p className="mode-description">{description}</p>
        </div>
    );
}
