import React, { Component } from 'react'
import { connect } from 'react-redux'
import * as modalAction from '../../ducks/ui/modal'
import ModalList from './ModalList'

class PureModal extends Component {

    constructor(props, context) {
        super(props, context)
    }

    render() {
        const { activeModal, hideModal } = this.props
        const ActiveModal = _.find(ModalList, m => m.name === activeModal )
        return(
            activeModal ?
                <div>
                    <div className="modal-backdrop fade in"></div>
                    <ActiveModal hideModal={ hideModal }/>
                </div>
                : <div/>
        )
    }
}

export default connect(
    state => ({
        activeModal: state.ui.modal.activeModal
    }),
    {
        hideModal: modalAction.hideModal
    }
)(PureModal)
