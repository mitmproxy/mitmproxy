import React, { Component } from 'react'
import { connect } from 'react-redux'
import * as modalAction from '../../ducks/ui/modal'
import Option from './OptionMaster'

class PureOptionModal extends Component {

    constructor(props, context) {
        super(props, context)
        this.state = { title: 'Options' }
    }

    render() {
        const { hideModal, options } = this.props
        const { title } = this.state
        return (
            <div>
                <div className="modal-header">
                    <button type="button" className="close" data-dismiss="modal" onClick={() => {
                        hideModal()
                    }}>
                        <i className="fa fa-fw fa-times"></i>
                    </button>
                    <div className="modal-title">
                        <h4>{ title }</h4>
                    </div>
                </div>

                <div className="modal-body">
                    <div className="container-fluid">
                    {
                        Object.keys(options).sort()
                            .map((key, index) => {
                                let option = options[key];
                                return (
                                    <Option
                                        key={index}
                                        name={key}
                                        option={option}
                                    />)
                            })
                    }
                    </div>
                </div>

                <div className="modal-footer">
                </div>
            </div>
        )
    }
}

export default connect(
    state => ({
        options: state.options
    }),
    {
        hideModal: modalAction.hideModal,
    }
)(PureOptionModal)
