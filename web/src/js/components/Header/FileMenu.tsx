import * as React from "react";
import FileChooser from "../common/FileChooser";
import Dropdown, { Divider, MenuItem } from "../common/Dropdown";
import * as flowsActions from "../../ducks/flows";
import HideInStatic from "../common/HideInStatic";
import { useAppDispatch, useAppSelector } from "../../ducks";

export default React.memo(function FileMenu() {
    const dispatch = useAppDispatch();
    const filter = useAppSelector((state) => state.flows.filter);
    return (
        <Dropdown
            className="pull-left special"
            text="File"
            options={{ placement: "bottom-start" }}
        >
            <li>
                <FileChooser
                    icon="fa-folder-open"
                    text="&nbsp;Open..."
                    onClick={
                        // stop event propagation: we must keep the input in DOM for upload to work.
                        (e) => e.stopPropagation()
                    }
                    onOpenFile={(file) => {
                        dispatch(flowsActions.upload(file));
                        document.body.click(); // "restart" event propagation
                    }}
                />
            </li>
            <MenuItem onClick={() => location.replace("/flows/dump")}>
                <i className="fa fa-fw fa-floppy-o" />
                &nbsp;Save
            </MenuItem>
            <MenuItem
                onClick={() => location.replace("/flows/dump?filter=" + filter)}
            >
                <i className="fa fa-fw fa-floppy-o" />
                &nbsp;Save filtered
            </MenuItem>
            <MenuItem
                onClick={() =>
                    confirm("Delete all flows?") &&
                    dispatch(flowsActions.clear())
                }
            >
                <i className="fa fa-fw fa-trash" />
                &nbsp;Clear All
            </MenuItem>
            <HideInStatic>
                <Divider />
                <li>
                    <a href="http://mitm.it/" target="_blank" rel="noreferrer">
                        <i className="fa fa-fw fa-external-link" />
                        &nbsp;Install Certificates...
                    </a>
                </li>
            </HideInStatic>
        </Dropdown>
    );
});
