import * as React from "react";
import { useTranslation } from "react-i18next";
import { useAppDispatch, useAppSelector } from "../../ducks";
import type { SocksState } from "../../modes/socks";
import { getSpec } from "../../modes/socks";
import type { ServerInfo } from "../../ducks/backendState";
import {
    setActive,
    setListenHost,
    setListenPort,
} from "../../ducks/modes/socks";

import { ModeToggle } from "./ModeToggle";
import { ServerStatus } from "./CaptureSetup";
import ValueEditor from "../editors/ValueEditor";
import { Popover } from "./Popover";

export default function Socks() {
    const { t } = useTranslation();
    const serverState = useAppSelector((state) => state.modes.socks);
    const backendState = useAppSelector((state) => state.backendState.servers);

    const servers = serverState.map((server) => {
        return (
            <SocksRow
                key={server.ui_id}
                server={server}
                backendState={backendState[getSpec(server)]}
            />
        );
    });

    return (
        <div>
            <h4 className="mode-title">{t("modes.socks.title")}</h4>
            <p className="mode-description">{t("modes.socks.description")}</p>

            {servers}
        </div>
    );
}

function SocksRow({
    server,
    backendState,
}: {
    server: SocksState;
    backendState?: ServerInfo;
}) {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();

    const error = server.error || backendState?.last_exception || undefined;

    return (
        <div>
            <ModeToggle
                value={server.active}
                label={t("modes.socks.toggleLabel")}
                onChange={() =>
                    dispatch(setActive({ server, value: !server.active }))
                }
            >
                <Popover iconClass="fa fa-cog">
                    <h4>{t("modes.socks.advancedConfig")}</h4>
                    <p>{t("modes.socks.listenHost")}</p>
                    <ValueEditor
                        className="mode-input"
                        content={server.listen_host || ""}
                        onEditDone={(host) =>
                            dispatch(setListenHost({ server, value: host }))
                        }
                    />

                    <p>{t("modes.socks.listenPort")}</p>
                    <ValueEditor
                        className="mode-input"
                        content={
                            server.listen_port
                                ? server.listen_port.toString()
                                : ""
                        }
                        placeholder={t("modes.socks.portPlaceholder")}
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
