import React, { Component } from "react"
import { connect } from "react-redux"
import * as modalAction from "../../ducks/ui/modal"
import * as optionAction from "../../ducks/options"
import Option from "./Option"
import _ from "lodash"

function PureOptionHelp({help}){
    return <div className="help-block small">{help}</div>;
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

export function PureOptionDefault({value, defaultVal}){
    if( value === defaultVal ) {
        return null
    } else {
        if (typeof(defaultVal) === 'boolean') {
            defaultVal = defaultVal ? 'true' : 'false'
        } else if (Array.isArray(defaultVal)){
            if (_.isEmpty(_.compact(value)) && // filter the empty string in array
                _.isEmpty(defaultVal)){
                return null
            }
            defaultVal = '[ ]'
        } else if (defaultVal === ''){
            defaultVal = '\"\"'
        } else if (defaultVal === null){
            defaultVal = 'null'
        }
        return <div className="small">Default: <strong> {defaultVal} </strong> </div>
    }
}
const OptionDefault = connect((state, {name}) => ({
    value: state.options[name].value,
    defaultVal: state.options[name].default
}))(PureOptionDefault)

class PureOptionModal extends Component {

    constructor(props, context) {
        super(props, context)
        this.state = { title: 'Options' }
    }

    componentWillUnmount(){
        // this.props.save()
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
                    <div className="form-horizontal">
                        {
                            options.map(name =>
                                <div key={name} className="form-group">
                                    <div className="col-xs-6">
                                        <label htmlFor={name}>{name}</label>
                                        <OptionHelp name={name}/>
                                    </div>
                                    <div className="col-xs-6">
                                        <Option name={name}/>
                                        <OptionError name={name}/>
                                        <OptionDefault name={name}/>
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
        options: Object.keys(state.options).sort()
    }),
    {
        hideModal: modalAction.hideModal,
        save: optionAction.save,
    }
)(PureOptionModal)
