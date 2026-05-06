import * as React from "react";
import { useTranslation } from "react-i18next";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import type { WireguardState } from "../../modes/wireguard";
import { getSpec } from "../../modes/wireguard";
import {
    setActive,
    setFilePath,
    setListenHost,
    setListenPort,
} from "../../ducks/modes/wireguard";
import { Popover } from "./Popover";
import ValueEditor from "../editors/ValueEditor";
import type { ServerInfo } from "../../ducks/backendState";
import { ServerStatus } from "./CaptureSetup";

export default function Wireguard() {
    const { t } = useTranslation();
    const serverState = useAppSelector((state) => state.modes.wireguard);
    const backendState = useAppSelector((state) => state.backendState.servers);

    const servers = serverState.map((server) => {
        return (
            <WireGuardRow
                key={server.ui_id}
                server={server}
                backendState={backendState[getSpec(server)]}
            />
        );
    });

    return (
        <div>
            <h4 className="mode-title">{t("modes.wireguard.title")}</h4>
            <p className="mode-description">{t("modes.wireguard.description")}</p>
            {servers}
        </div>
    );
}

function WireGuardRow({
    server,
    backendState,
}: {
    server: WireguardState;
    backendState?: ServerInfo;
}) {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();

    const error = server.error || backendState?.last_exception || undefined;

    return (
        <div>
            <ModeToggle
                value={server.active}
                label={t("modes.wireguard.toggleLabel")}
                onChange={() =>
                    dispatch(setActive({ server, value: !server.active }))
                }
            >
                <Popover iconClass="fa fa-cog">
                    <h4>{t("modes.wireguard.advancedConfig")}</h4>
                    <p>{t("modes.wireguard.listenHost")}</p>
                    <ValueEditor
                        className="mode-input"
                        content={server.listen_host || ""}
                        placeholder={t("modes.wireguard.hostPlaceholder")}
                        onEditDone={(host) =>
                            dispatch(setListenHost({ server, value: host }))
                        }
                    />
                    <p>{t("modes.wireguard.listenPort")}</p>
                    <ValueEditor
                        className="mode-input"
                        content={
                            server.listen_port
                                ? server.listen_port.toString()
                                : ""
                        }
                        placeholder={t("modes.wireguard.portPlaceholder")}
                        onEditDone={(port) =>
                            dispatch(
                                setListenPort({
                                    server,
                                    value: parseInt(port),
                                }),
                            )
                        }
                    />
                    <p>{t("modes.wireguard.configFile")}</p>
                    <ValueEditor
                        className="mode-input"
                        content={server.file_path || ""}
                        placeholder={t("modes.wireguard.filePlaceholder")}
                        onEditDone={(path) =>
                            dispatch(setFilePath({ server, value: path }))
                        }
                    />
                </Popover>
            </ModeToggle>
            <ServerStatus error={error} backendState={backendState} />
        </div>
    );
}
