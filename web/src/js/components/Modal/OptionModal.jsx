import React, { Component } from "react"
import { connect } from "react-redux"
import * as modalAction from "../../ducks/ui/modal"
import Option from "./Option"

function PureOptionHelp({help}){
    return <div className="small text-muted">{help}</div>;
}
const OptionHelp = connect((state, {name}) => ({
    help: state.options[name].help,
}))(PureOptionHelp);

function PureOptionError({error}){
    if(!error) return null;
    return <div className="small text-danger">{error}</div>;
}
const OptionError = connect((state, {name}) => ({
    error: state.ui.optionsEditor[name] && state.ui.optionsEditor[name].error
}))(PureOptionError);

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
                            options.map(name =>
                                <div key={name} className="row">
                                    <div className="col-xs-6">
                                        {name}
                                        <OptionHelp name={name}/>
                                    </div>
                                    <div className="col-xs-6">
                                        <Option name={name}/>
                                        <OptionError name={name}/>
                                    </div>
                                </div>
                            )
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
        options: Object.keys(state.options)
    }),
    {
        hideModal: modalAction.hideModal,
    }
)(PureOptionModal)
