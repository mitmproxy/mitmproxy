import React, { PropTypes, Component } from 'react'
import { connect } from 'react-redux'

import {closeFlowEditor} from '../../ducks/ui.js'
import {openFlowEditor} from '../../ducks/ui.js'

// FlowEditorButton.propTypes = {
//     isFlowEditorOpen: PropTypes.bool.isRequired,
//     content: PropTypes.string.isRequired,
//     onContentChange: PropTypes.func.isRequired
// }

class FlowEditorButton extends Component{
     static propTypes = {
        isFlowEditorOpen: PropTypes.bool.isRequired,
        content: PropTypes.string.isRequired,
        onContentChange: PropTypes.func.isRequired
     }

    render(){
        let { isFlowEditorOpen, closeFlowEditor, openFlowEditor,  onContentChange, content } = this.props
        return (
            <div className="edit-flow-container">
                {isFlowEditorOpen ?
                    <a className="edit-flow" onClick={() => {onContentChange(content); closeFlowEditor()}}>
                        <i className="fa fa-check"/>
                    </a>
                    :
                    <a  className="edit-flow" onClick={() => openFlowEditor()}>
                        <i className="fa fa-pencil"/>
                    </a>
                }
            </div>
        )
    }
}

export default connect(
    state => ({
        isFlowEditorOpen: state.ui.isFlowEditorOpen,
        content: state.flows.modifiedFlow.content
    }),
    {
        closeFlowEditor,
        openFlowEditor

    }
)(FlowEditorButton)
