import * as React from "react";
import { useTranslation } from "react-i18next";
import type { TransparentState } from "../../modes/transparent";
import { getSpec } from "../../modes/transparent";
import type { ServerInfo } from "../../ducks/backendState";
import {
    setActive,
    setListenHost,
    setListenPort,
} from "../../ducks/modes/transparent";

import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { ServerStatus } from "./CaptureSetup";
import ValueEditor from "../editors/ValueEditor";
import { Popover } from "./Popover";

export default function Transparent() {
    const { t } = useTranslation();
    const serverState = useAppSelector((state) => state.modes.transparent);
    const backendState = useAppSelector((state) => state.backendState.servers);

    const servers = serverState.map((server) => {
        return (
            <TransparentRow
                key={server.ui_id}
                server={server}
                backendState={backendState[getSpec(server)]}
            />
        );
    });

    return (
        <div>
            <h4 className="mode-title">{t("modes.transparent.title")}</h4>
            <p className="mode-description">
                {t("modes.transparent.description").replace(
                    "configure your routing table",
                    "",
                )}
                <a
                    href="https://docs.mitmproxy.org/stable/howto-transparent/"
                    style={{ textDecoration: "underline", color: "inherit" }}
                >
                    {t("modes.transparent.configureRoutingTable")}
                </a>{" "}
                {t("modes.transparent.description").split(
                    "configure your routing table",
                )[1] || ""}
            </p>

            {servers}
        </div>
    );
}

function TransparentRow({
    server,
    backendState,
}: {
    server: TransparentState;
    backendState?: ServerInfo;
}) {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();

    const error = server.error || backendState?.last_exception || undefined;

    return (
        <div>
            <ModeToggle
                value={server.active}
                label={t("modes.transparent.toggleLabel")}
                onChange={() =>
                    dispatch(setActive({ server, value: !server.active }))
                }
            >
                <Popover iconClass="fa fa-cog">
                    <h4>{t("modes.transparent.advancedConfig")}</h4>
                    <p>{t("modes.transparent.listenHost")}</p>
                    <ValueEditor
                        className="mode-input"
                        content={server.listen_host || ""}
                        onEditDone={(host) =>
                            dispatch(setListenHost({ server, value: host }))
                        }
                    />

                    <p>{t("modes.transparent.listenPort")}</p>
                    <ValueEditor
                        className="mode-input"
                        content={
                            server.listen_port
                                ? server.listen_port.toString()
                                : ""
                        }
                        placeholder={t("modes.transparent.portPlaceholder")}
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
