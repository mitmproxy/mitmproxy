import React from 'react'
import {useDispatch} from 'react-redux'
import FileChooser from '../common/FileChooser'
import Dropdown, {Divider, MenuItem} from '../common/Dropdown'
import * as flowsActions from '../../ducks/flows'
import HideInStatic from "../common/HideInStatic";


export default React.memo(function FileMenu() {
    const dispatch = useDispatch();
    return (
        <Dropdown className="pull-left special" text="mitmproxy" options={{"placement": "bottom-start"}}>
            <MenuItem onClick={() => confirm('Delete all flows?') && dispatch(flowsActions.clear())}>
                <i className="fa fa-fw fa-trash"/>&nbsp;Clear All
            </MenuItem>
            <li>
                <FileChooser
                    icon="fa-folder-open"
                    text="&nbsp;Open..."
                    onOpenFile={file => dispatch(flowsActions.upload(file))}
                />
            </li>
            <MenuItem onClick={() => dispatch(flowsActions.download())}>
                <i className="fa fa-fw fa-floppy-o"/>&nbsp;Save...
            </MenuItem>
            <HideInStatic>
                <Divider/>
                <li>
                    <a href="http://mitm.it/" target="_blank">
                        <i className="fa fa-fw fa-external-link"/>&nbsp;Install Certificates...
                    </a>
                </li>
            </HideInStatic>
        </Dropdown>
    )
});
