import * as React from "react";
import { useTranslation } from "react-i18next";
import { useAppDispatch, useAppSelector } from "../../ducks";
import type { ServerInfo } from "../../ducks/backendState";
import ValueEditor from "../editors/ValueEditor";
import { ServerStatus } from "./CaptureSetup";
import { ModeToggle } from "./ModeToggle";
import { setActive, setListenHost, setListenPort } from "../../ducks/modes/dns";
import type { DnsState } from "../../modes/dns";
import { getSpec } from "../../modes/dns";
import { Popover } from "./Popover";

export default function Dns() {
    const { t } = useTranslation();
    const serverState = useAppSelector((state) => state.modes.dns);
    const backendState = useAppSelector((state) => state.backendState.servers);

    const servers = serverState.map((server) => {
        return (
            <DnsRow
                key={server.ui_id}
                server={server}
                backendState={backendState[getSpec(server)]}
            />
        );
    });

    return (
        <div>
            <h4 className="mode-title">{t("modes.dns.title")}</h4>
            <p className="mode-description">{t("modes.dns.description")}</p>
            {servers}
        </div>
    );
}

function DnsRow({
    server,
    backendState,
}: {
    server: DnsState;
    backendState?: ServerInfo;
}) {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();

    const error = server.error || backendState?.last_exception || undefined;

    return (
        <div>
            <ModeToggle
                value={server.active}
                label={t("modes.dns.toggleLabel")}
                onChange={() =>
                    dispatch(setActive({ server, value: !server.active }))
                }
            >
                <Popover iconClass="fa fa-cog">
                    <h4>{t("modes.dns.advancedConfig")}</h4>
                    <p>{t("modes.dns.listenHost")}</p>
                    <ValueEditor
                        className="mode-input"
                        content={server.listen_host || ""}
                        onEditDone={(host) =>
                            dispatch(setListenHost({ server, value: host }))
                        }
                    />

                    <p>{t("modes.dns.listenPort")}</p>
                    <ValueEditor
                        className="mode-input"
                        content={
                            server.listen_port
                                ? server.listen_port.toString()
                                : ""
                        }
                        placeholder={t("modes.dns.portPlaceholder")}
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
