import React from 'react'
import PropTypes from 'prop-types'
import {connect} from 'react-redux'
import FileChooser from '../common/FileChooser'
import Dropdown, {Divider, MenuItem} from '../common/Dropdown'
import * as flowsActions from '../../ducks/flows'
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

export function FileMenu({clearFlows, loadFlows, saveFlows}) {
    return (
        <Dropdown className="pull-left special" text="mitmproxy" options={{"placement": "bottom-start"}}>
            <MenuItem onClick={e => FileMenu.onNewClick(e, clearFlows)}>
                <i className="fa fa-fw fa-trash"/>
                &nbsp;Clear All
            </MenuItem>
            <li>
                <FileChooser
                    icon="fa-folder-open"
                    text="&nbsp;Open..."
                    onOpenFile={file => loadFlows(file)}
                />
            </li>
            <MenuItem onClick={e => {
                e.preventDefault();
                saveFlows();
            }}>
                <i className="fa fa-fw fa-floppy-o"/>
                &nbsp;Save...
            </MenuItem>

            <HideInStatic>
                <Divider/>
                <li>
                    <a href="http://mitm.it/" target="_blank">
                        <i className="fa fa-fw fa-external-link"/>
                        &nbsp;Install Certificates...
                    </a>
                </li>
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
