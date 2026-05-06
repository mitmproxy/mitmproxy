import * as React from "react";
import { useTranslation } from "react-i18next";
import { useAppDispatch, useAppSelector } from "../../ducks";
import type { UpstreamState } from "../../modes/upstream";
import { getSpec } from "../../modes/upstream";
import type { ServerInfo } from "../../ducks/backendState";
import {
    setDestination,
    setActive,
    setListenHost,
    setListenPort,
} from "../../ducks/modes/upstream";
import ValueEditor from "../editors/ValueEditor";
import { ServerStatus } from "./CaptureSetup";
import { ModeToggle } from "./ModeToggle";
import { Popover } from "./Popover";

export default function Upstream() {
    const { t } = useTranslation();
    const serverState = useAppSelector((state) => state.modes.upstream);
    const backendState = useAppSelector((state) => state.backendState.servers);

    const servers = serverState.map((server) => {
        return (
            <UpstreamRow
                key={server.ui_id}
                server={server}
                backendState={backendState[getSpec(server)]}
            />
        );
    });

    return (
        <div>
            <h4 className="mode-title">{t("modes.upstream.title")}</h4>
            <p className="mode-description">{t("modes.upstream.description")}</p>
            {servers}
        </div>
    );
}

function UpstreamRow({
    server,
    backendState,
}: {
    server: UpstreamState;
    backendState?: ServerInfo;
}) {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();

    const error = server.error || backendState?.last_exception || undefined;

    return (
        <div>
            <ModeToggle
                value={server.active}
                label={t("modes.upstream.toggleLabel")}
                onChange={() => {
                    dispatch(setActive({ server, value: !server.active }));
                }}
            >
                <ValueEditor
                    className="mode-upstream-input"
                    content={server.destination?.toString() || ""}
                    onEditDone={(value) =>
                        dispatch(setDestination({ server, value }))
                    }
                    placeholder={t("modes.upstream.destinationPlaceholder")}
                />
                <Popover iconClass="fa fa-cog">
                    <h4>{t("modes.upstream.advancedConfig")}</h4>
                    <p>{t("modes.upstream.listenHost")}</p>
                    <ValueEditor
                        className="mode-input"
                        content={server.listen_host || ""}
                        onEditDone={(host) =>
                            dispatch(setListenHost({ server, value: host }))
                        }
                    />

                    <p>{t("modes.upstream.listenPort")}</p>
                    <ValueEditor
                        className="mode-input"
                        content={
                            server.listen_port
                                ? server.listen_port.toString()
                                : ""
                        }
                        placeholder={t("modes.upstream.portPlaceholder")}
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
