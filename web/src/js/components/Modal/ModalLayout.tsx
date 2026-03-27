import * as React from "react";

type ModalLayoutProps = {
    children: React.ReactNode;
};

export default function ModalLayout({ children }: ModalLayoutProps) {
    return (
        <div>
            <div className="modal-backdrop m-modal-backdrop fade in is-visible"></div>
            <div
                className="modal m-modal modal-visible is-visible"
                id="optionsModal"
                tabIndex={-1}
                role="dialog"
                aria-labelledby="options"
            >
                <div className="modal-dialog m-modal-dialog modal-lg m-modal-lg" role="document">
                    <div className="modal-content m-modal-content">{children}</div>
                </div>
            </div>
        </div>
    );
}
