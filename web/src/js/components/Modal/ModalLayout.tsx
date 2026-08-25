import * as React from "react";

type ModalLayoutProps = {
    children: React.ReactNode;
};

export default function ModalLayout({ children }: ModalLayoutProps) {
    return (
        <div>
            <div className="modal-backdrop is-visible"></div>
            <div
                className="modal is-visible"
                id="optionsModal"
                tabIndex={-1}
                role="dialog"
                aria-labelledby="options"
            >
                <div className="modal-dialog modal-lg" role="document">
                    <div className="modal-content">{children}</div>
                </div>
            </div>
        </div>
    );
}
