import * as React from "react";

type ModalLayoutProps = {
    children: React.ReactNode;
};

export default function ModalLayout({ children }: ModalLayoutProps) {
    return (
        <div>
            <div className="m-modal-backdrop is-visible"></div>
            <div
                className="m-modal is-visible"
                id="optionsModal"
                tabIndex={-1}
                role="dialog"
                aria-labelledby="options"
            >
                <div className="m-modal-dialog m-modal-lg" role="document">
                    <div className="m-modal-content">{children}</div>
                </div>
            </div>
        </div>
    );
}
