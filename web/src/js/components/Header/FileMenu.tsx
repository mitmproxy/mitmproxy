import * as React from "react";
import FileChooser from "../common/FileChooser";
import Dropdown, { Divider, MenuItem } from "../common/Dropdown";
import Icon from "../common/Icon";
import * as flowsActions from "../../ducks/flows";
import HideInStatic from "../common/HideInStatic";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { FilterName } from "../../ducks/ui/filter";

export default React.memo(function FileMenu() {
    const dispatch = useAppDispatch();
    const filter = useAppSelector(
        (state) => state.ui.filter[FilterName.Search],
    );
    return (
        <Dropdown
            className="pull-left special"
            text="File"
            options={{ placement: "bottom-start" }}
        >
            <li>
                <FileChooser
                    icon="openFolder"
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
                <Icon name="save" />
                &nbsp;Save
            </MenuItem>
            <MenuItem
                onClick={() => location.replace("/flows/dump?filter=" + filter)}
            >
                <Icon name="save" />
                &nbsp;Save filtered
            </MenuItem>
            <MenuItem
                onClick={() =>
                    confirm("Delete all flows?") &&
                    dispatch(flowsActions.clear())
                }
            >
                <Icon name="delete" />
                &nbsp;Clear All
            </MenuItem>
            <HideInStatic>
                <Divider />
                <li>
                    <a href="http://mitm.it/" target="_blank" rel="noreferrer">
                        <Icon name="external" />
                        &nbsp;Install Certificates
                    </a>
                </li>
            </HideInStatic>
        </Dropdown>
    );
});
