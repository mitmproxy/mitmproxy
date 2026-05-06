import * as React from "react";
import { useTranslation } from "react-i18next";
import FileChooser from "../common/FileChooser";
import Dropdown, { Divider, MenuItem } from "../common/Dropdown";
import * as flowsActions from "../../ducks/flows";
import HideInStatic from "../common/HideInStatic";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { FilterName } from "../../ducks/ui/filter";

export default React.memo(function FileMenu() {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();
    const filter = useAppSelector(
        (state) => state.ui.filter[FilterName.Search],
    );
    return (
        <Dropdown
            className="pull-left special"
            text={t("header.fileMenu.title")}
            options={{ placement: "bottom-start" }}
        >
            <li>
                <FileChooser
                    icon="fa-folder-open"
                    text={" " + t("header.fileMenu.open")}
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
                &nbsp;{t("header.fileMenu.save")}
            </MenuItem>
            <MenuItem
                onClick={() => location.replace("/flows/dump?filter=" + filter)}
            >
                <i className="fa fa-fw fa-floppy-o" />
                &nbsp;{t("header.fileMenu.saveFiltered")}
            </MenuItem>
            <MenuItem
                onClick={() =>
                    confirm(t("header.fileMenu.confirmDeleteAll")) &&
                    dispatch(flowsActions.clear())
                }
            >
                <i className="fa fa-fw fa-trash" />
                &nbsp;{t("header.fileMenu.clearAll")}
            </MenuItem>
            <HideInStatic>
                <Divider />
                <li>
                    <a href="http://mitm.it/" target="_blank" rel="noreferrer">
                        <i className="fa fa-fw fa-external-link" />
                        &nbsp;{t("header.fileMenu.installCerts")}
                    </a>
                </li>
            </HideInStatic>
        </Dropdown>
    );
});
