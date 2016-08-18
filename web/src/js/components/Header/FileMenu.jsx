import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import classnames from 'classnames'
import FileChooser from '../common/FileChooser'
import Dropdown from '../common/Dropdown'
import * as flowsActions from '../../ducks/flows'



class FileMenu extends Component {

    static propTypes = {
        clearFlows: PropTypes.func.isRequired,
        loadFlows: PropTypes.func.isRequired,
        saveFlows: PropTypes.func.isRequired
    }

    constructor(props, context) {
        super(props, context)

        this.onNewClick = this.onNewClick.bind(this)
        this.onOpenClick = this.onOpenClick.bind(this)
        this.onOpenFile = this.onOpenFile.bind(this)
        this.onSaveClick = this.onSaveClick.bind(this)
    }

    onNewClick(e) {
        e.preventDefault()
        if (confirm('Delete all flows?')) {
            this.props.clearFlows()
        }
    }
    
    onOpenFile(file) {
        this.props.loadFlows(file)
    }

    onSaveClick(e) {
        e.preventDefault()
        this.props.saveFlows()
    }

    render() {
        return (
            <Dropdown className="pull-left" btnClass="special" text="mitmproxy">
                <a href="#" onClick={this.onNewClick}>
                    <i className="fa fa-fw fa-file"></i>
                    New
                </a>
                <FileChooser
                    icon="fa-folder-open"
                    text="Open..."
                    onOpenFile={this.onOpenFile}
                />
                <a href="#" onClick={this.onSaveClick}>
                    <i className="fa fa-fw fa-floppy-o"></i>
                    Save...
                </a>

                <span name="divider"/>

                <a href="http://mitm.it/" target="_blank">
                        <i className="fa fa-fw fa-external-link"></i>
                        Install Certificates...
                </a>
            </Dropdown>
        )
    }
}

export default connect(
    null,
    {
        clearFlows: flowsActions.clear,
        loadFlows: flowsActions.upload,
        saveFlows: flowsActions.download,
    }
)(FileMenu)
