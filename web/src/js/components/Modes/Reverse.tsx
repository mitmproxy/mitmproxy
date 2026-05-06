import * as React from "react";
import { useTranslation } from "react-i18next";
import { ModeToggle } from "./ModeToggle";
import { useAppDispatch, useAppSelector } from "../../ducks";
import {
    addServer,
    removeServer,
    setActive,
    setDestination,
    setListenHost,
    setListenPort,
    setProtocol,
} from "../../ducks/modes/reverse";
import type { ReverseState } from "../../modes/reverse";
import { getSpec } from "../../modes/reverse";
import { ReverseProxyProtocols } from "../../backends/consts";
import type { ServerInfo } from "../../ducks/backendState";
import ValueEditor from "../editors/ValueEditor";
import { ServerStatus } from "./CaptureSetup";
import { Popover } from "./Popover";

interface ReverseToggleRowProps {
    removable: boolean;
    server: ReverseState;
    backendState?: ServerInfo;
}

export default function Reverse() {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();

    const servers = useAppSelector((state) => state.modes.reverse);
    const backendState = useAppSelector((state) => state.backendState.servers);

    return (
        <div>
            <h4 className="mode-title">{t("modes.reverse.title")}</h4>
            <p className="mode-description">{t("modes.reverse.description")}</p>
            <div className="mode-reverse-servers">
                {servers.map((server, i) => (
                    <ReverseToggleRow
                        key={server.ui_id}
                        removable={i > 0}
                        server={server}
                        backendState={backendState[getSpec(server)]}
                    />
                ))}
                <div
                    className="mode-reverse-add-server"
                    onClick={() => dispatch(addServer())}
                >
                    <i className="fa fa-plus-square-o" aria-hidden="true"></i> {t("modes.reverse.addServer")}
                </div>
            </div>
        </div>
    );
}

function ReverseToggleRow({
    removable,
    server,
    backendState,
}: ReverseToggleRowProps) {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();

    const protocols = Object.values(ReverseProxyProtocols);

    const deleteServer = async () => {
        if (server.active) {
            await dispatch(setActive({ server, value: false })).unwrap();
        }
        await dispatch(removeServer(server));
    };

    const error = server.error || backendState?.last_exception || undefined;

    return (
        <div>
            <ModeToggle
                value={server.active}
                label={t("modes.reverse.toggleLabel")}
                onChange={() => {
                    dispatch(setActive({ server, value: !server.active }));
                }}
            >
                <select
                    name="protocols"
                    className="mode-reverse-dropdown"
                    value={server.protocol}
                    onChange={(e) => {
                        dispatch(
                            setProtocol({
                                server,
                                value: e.target.value as ReverseProxyProtocols,
                            }),
                        );
                    }}
                >
                    {protocols.map((prot) => (
                        <option key={prot} value={prot}>
                            {prot}
                        </option>
                    ))}
                </select>
                {t("modes.reverse.trafficTo")}
                <ValueEditor
                    className="mode-reverse-input"
                    content={server.destination?.toString() || ""}
                    onEditDone={(value) =>
                        dispatch(setDestination({ server, value }))
                    }
                    placeholder={t("modes.reverse.destinationPlaceholder")}
                />
                <Popover iconClass="fa fa-cog">
                    <h4>{t("modes.reverse.advancedConfig")}</h4>
                    <p>{t("modes.reverse.listenHost")}</p>
                    <ValueEditor
                        className="mode-input"
                        content={server.listen_host || ""}
                        onEditDone={(value) =>
                            dispatch(setListenHost({ server, value }))
                        }
                        placeholder={t("modes.reverse.hostPlaceholder")}
                    />
                    <p>{t("modes.reverse.listenPort")}</p>
                    <ValueEditor
                        className="mode-input"
                        content={String(server.listen_port || "")}
                        onEditDone={(value) =>
                            dispatch(
                                setListenPort({
                                    server,
                                    value: value as unknown as number,
                                }),
                            )
                        }
                        placeholder={t("modes.reverse.portPlaceholder")}
                    />
                </Popover>
                {removable && (
                    <i
                        className="fa fa-fw fa-trash fa-lg"
                        aria-hidden="true"
                        onClick={deleteServer}
                    ></i>
                )}
            </ModeToggle>
            <ServerStatus error={error} backendState={backendState} />
        </div>
    );
}
