import React from 'react'
import PropTypes from 'prop-types'

OptionModal.prototype = {
    hideModal: PropTypes.function,
}

export default function OptionModal( { hideModal }) {
    const title = 'Options'
    return (
        <div className="modal modal-visible" id="optionsModal" tabIndex="-1" role="dialog" aria-labelledby="options">
        <div className="modal-dialog modal-lg" role="document">
            <div className="modal-content">
                <div className="modal-header">
                    <button type="button" className="close" data-dismiss="modal" onClick={() => { hideModal() }}>
                        <i className="fa fa-fw fa-times"></i>
                    </button>
                    <div className="modal-title">
                        <h4>{ title }</h4>
                    </div>
                </div>

                <div className="modal-body">
                </div>

                <div className="modal-footer">
                    <button type="button" className="btn btn-primary">Save Changes</button>
                </div>
            </div>
        </div>
    </div>
    )
}
