import * as React from "react";
import { useTranslation } from "react-i18next";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { setActive, setSelectedProcesses } from "../../ducks/modes/local";
import type { LocalState } from "../../modes/local";
import { getSpec } from "../../modes/local";
import { ServerStatus } from "./CaptureSetup";
import type { ServerInfo } from "../../ducks/backendState";
import LocalDropdown from "./LocalDropdown";
import { fetchProcesses } from "../../ducks/processes";

export default function Local() {
    const { t } = useTranslation();
    const serverState = useAppSelector((state) => state.modes.local);
    const backendState = useAppSelector((state) => state.backendState.servers);

    const servers = serverState.map((server) => {
        return (
            <LocalRow
                key={server.ui_id}
                server={server}
                backendState={backendState[getSpec(server)]}
            />
        );
    });

    return (
        <div>
            <h4 className="mode-title">{t("modes.local.title")}</h4>
            <p className="mode-description">{t("modes.local.description")}</p>
            {servers}
        </div>
    );
}

function LocalRow({
    server,
    backendState,
}: {
    server: LocalState;
    backendState?: ServerInfo;
}) {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();

    const fetchProcessesError = useAppSelector(
        (state) => state.processes.error,
    );

    const error =
        server.error ||
        backendState?.last_exception ||
        fetchProcessesError ||
        undefined;

    const handleDeletionProcess = (process: string) => {
        const newSelectedProcesses = server.selectedProcesses
            ?.split(/,\s*/)
            .filter((p) => p !== process)
            .join(", ");

        dispatch(
            setSelectedProcesses({
                server,
                value: newSelectedProcesses,
            }),
        );
    };

    return (
        <div className="mode-local">
            <ModeToggle
                value={server.active}
                label={t("modes.local.toggleLabel")}
                onChange={() =>
                    dispatch(setActive({ server, value: !server.active }))
                }
            >
                <div className="processes-container">
                    <div className="selected-processes">
                        {server.selectedProcesses
                            ?.split(/,\s*/)
                            .filter((p) => p.trim() !== "")
                            .map((p) => (
                                <div key={p} className="selected-process">
                                    {p}
                                    <i
                                        className="fa fa-times"
                                        aria-hidden="true"
                                        onClick={() => handleDeletionProcess(p)}
                                    ></i>
                                </div>
                            ))}
                    </div>
                    <div className="dropdown-container">
                        <LocalDropdown server={server} />
                        <i
                            className="fa fa-refresh"
                            aria-hidden="true"
                            onClick={() => dispatch(fetchProcesses())}
                        ></i>
                    </div>
                </div>
            </ModeToggle>
            <ServerStatus error={error} backendState={backendState} />
        </div>
    );
}
