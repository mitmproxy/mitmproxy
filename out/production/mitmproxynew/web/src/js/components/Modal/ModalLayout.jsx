import React from 'react'

export default function ModalLayout ({ children }) {
    return (
        <div>
        <div className="modal-backdrop fade in"></div>
        <div className="modal modal-visible" id="optionsModal" tabIndex="-1" role="dialog" aria-labelledby="options">
        <div className="modal-dialog modal-lg" role="document">
            <div className="modal-content">
                {children}
            </div>
        </div>
    </div>
        </div>
    )
}
