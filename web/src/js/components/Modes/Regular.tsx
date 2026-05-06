import * as React from "react";
import { useTranslation } from "react-i18next";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import {
    setListenPort,
    setActive,
    setListenHost,
} from "../../ducks/modes/regular";
import ValueEditor from "../editors/ValueEditor";
import type { RegularState } from "../../modes/regular";
import { getSpec } from "../../modes/regular";
import { Popover } from "./Popover";
import type { ServerInfo } from "../../ducks/backendState";
import { ServerStatus } from "./CaptureSetup";

export default function Regular() {
    const { t } = useTranslation();
    const serverState = useAppSelector((state) => state.modes.regular);
    const backendState = useAppSelector((state) => state.backendState.servers);

    const servers = serverState.map((server) => {
        return (
            <RegularRow
                key={server.ui_id}
                server={server}
                backendState={backendState[getSpec(server)]}
            />
        );
    });

    return (
        <div>
            <h4 className="mode-title">{t("modes.regular.title")}</h4>
            <p className="mode-description">
                {t("modes.regular.description")}
            </p>
            {servers}
        </div>
    );
}

function RegularRow({
    server,
    backendState,
}: {
    server: RegularState;
    error?: string;
    backendState?: ServerInfo;
}) {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();

    const error = server.error || backendState?.last_exception || undefined;

    return (
        <div>
            <ModeToggle
                value={server.active}
                label={t("modes.regular.toggleLabel")}
                onChange={() =>
                    dispatch(setActive({ server, value: !server.active }))
                }
            >
                <Popover iconClass="fa fa-cog">
                    <h4>{t("modes.regular.advancedConfig")}</h4>
                    <p>{t("modes.regular.listenHost")}</p>
                    <ValueEditor
                        className="mode-input"
                        content={server.listen_host || ""}
                        onEditDone={(host) =>
                            dispatch(setListenHost({ server, value: host }))
                        }
                    />

                    <p>{t("modes.regular.listenPort")}</p>
                    <ValueEditor
                        className="mode-input"
                        content={
                            server.listen_port
                                ? server.listen_port.toString()
                                : ""
                        }
                        placeholder={t("modes.regular.portPlaceholder")}
                        onEditDone={(port) =>
                            dispatch(
                                setListenPort({
                                    server,
                                    value: parseInt(port),
                                }),
                            )
                        }
                    />
                </Popover>
            </ModeToggle>
            <ServerStatus error={error} backendState={backendState} />
        </div>
    );
}
