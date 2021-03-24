import React, { Component } from "react"
import { connect } from "react-redux"
import * as modalAction from "../../ducks/ui/modal"
import Clipboard from 'react-clipboard.js';
import * as flowsActions from "../../ducks/flows"


class PureCopyModal extends Component {

    constructor(props, context) {
        super(props, context)
        this.state = { title: 'Curl', curl: '' }
    }

    componentDidMount() {
        const { flow, copyFlow } = this.props
        copyFlow(flow)
        .then(res => res.json())
        .then((result) => {
            this.setState({
                curl: result.curl
            })
          }
        )
      }

    render() {
        const { hideModal} = this.props
        const { title, curl } = this.state
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
                    <div style={{overflowWrap: 'break-word'}} id="curl">{curl}</div>
                </div>

                <div className="modal-footer">
                    <Clipboard className="btn btn-primary" data-clipboard-target="#curl">copy</Clipboard>
                </div>
            </div>
        )
    }
}

export default connect(
    state => ({
        flow: state.flows.byId[state.flows.selected[0]],
    }),
    {
        hideModal: modalAction.hideModal,
        copyFlow: flowsActions.copy
    }
)(PureCopyModal)
