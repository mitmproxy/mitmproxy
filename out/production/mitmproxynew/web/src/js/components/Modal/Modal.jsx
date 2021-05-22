import React, { Component } from 'react'
import { connect } from 'react-redux'
import ModalList from './ModalList'

class PureModal extends Component {

    constructor(props, context) {
        super(props, context)
    }

    render() {
        const { activeModal } = this.props
        const ActiveModal = ModalList.find(m => m.name === activeModal )
        return(
            activeModal ? <ActiveModal/> : <div/>
        )
    }
}

export default connect(
    state => ({
        activeModal: state.ui.modal.activeModal
    })
)(PureModal)
