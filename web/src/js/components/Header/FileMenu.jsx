import React, { Component } from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import FileChooser from '../common/FileChooser'
import Dropdown, {Divider} from '../common/Dropdown'
import * as flowsActions from '../../ducks/flows'
import * as modalActions from '../../ducks/ui/modal'
import HideInStatic from "../common/HideInStatic";

FileMenu.propTypes = {
    clearFlows: PropTypes.func.isRequired,
    loadFlows: PropTypes.func.isRequired,
    saveFlows: PropTypes.func.isRequired,
}

FileMenu.onNewClick = (e, clearFlows) => {
    e.preventDefault();
    if (confirm('Delete all flows?'))
        clearFlows()
}

export function FileMenu ({clearFlows, loadFlows, saveFlows}) {
     return (
        <Dropdown className="pull-left" btnClass="special" text="mitmproxy">
            <a href="#" onClick={e => FileMenu.onNewClick(e, clearFlows)}>
                <i className="fa fa-fw fa-trash"></i>
                &nbsp;Clear All
            </a>
            <FileChooser
                icon="fa-folder-open"
                text="&nbsp;Open..."
                onOpenFile={file => loadFlows(file)}
            />
            <a href="#" onClick={e =>{ e.preventDefault(); saveFlows();}}>
                <i className="fa fa-fw fa-floppy-o"></i>
                &nbsp;Save...
            </a>

            <HideInStatic>
            <Divider/>
            <a href="http://mitm.it/" target="_blank">
                <i className="fa fa-fw fa-external-link"></i>
                &nbsp;Install Certificates...
            </a>
            </HideInStatic>
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
