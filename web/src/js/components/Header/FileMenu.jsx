import React, { Component, PropTypes } from 'react'
import { connect } from 'react-redux'
import FileChooser from '../common/FileChooser'
import Dropdown, {Divider} from '../common/Dropdown'
import * as flowsActions from '../../ducks/flows'

FileMenu.propTypes = {
    clearFlows: PropTypes.func.isRequired,
    loadFlows: PropTypes.func.isRequired,
    saveFlows: PropTypes.func.isRequired
}

FileMenu.onNewClick = (e, clearFlows) => {
    e.preventDefault();
    if (confirm('Delete all flows?'))
        clearFlows()
}

function FileMenu ({clearFlows, loadFlows, saveFlows}) {
     return (
        <Dropdown className="pull-left" btnClass="special" text="mitmproxy">
            <a href="#" onClick={e => FileMenu.onNewClick(e, clearFlows)}>
                <i className="fa fa-fw fa-file"></i>
                New
            </a>
            <FileChooser
                icon="fa-folder-open"
                text="Open..."
                onOpenFile={file => loadFlows(file)}
            />
            <a href="#" onClick={e =>{ e.preventDefault(); saveFlows();}}>
                <i className="fa fa-fw fa-floppy-o"></i>
                Save...
            </a>

            <Divider/>

            <a href="http://mitm.it/" target="_blank">
                <i className="fa fa-fw fa-external-link"></i>
                Install Certificates...
            </a>
        </Dropdown>
    )
}

export default connect(
    null,
    {
        clearFlows: flowsActions.clear,
        loadFlows: flowsActions.upload,
        saveFlows: flowsActions.download,
    }
)(FileMenu)
