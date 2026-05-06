import * as React from "react";
import { useTranslation } from "react-i18next";
import Local from "./Modes/Local";
import Regular from "./Modes/Regular";
import Wireguard from "./Modes/Wireguard";
import Reverse from "./Modes/Reverse";
import { useAppSelector } from "../ducks";
import Transparent from "./Modes/Transparent";
import Socks from "./Modes/Socks";
import Upstream from "./Modes/Upstream";
import Dns from "./Modes/Dns";
import MissingMode from "./Modes/MissingMode";

export default function Modes() {
    const { t } = useTranslation();
    const { platform, localModeUnavailable } = useAppSelector(
        (state) => state.backendState,
    );

    return (
        <div className="modes">
            <h2>{t("modes.title")}</h2>
            <p>{t("modes.description")}</p>

            <div className="modes-category green-left-border">
                <h3>{t("modes.recommended")}</h3>
                <div className="modes-container">
                    <Regular />
                    {localModeUnavailable !== null ? (
                        <MissingMode
                            title={t("modes.localRedirectMissingTitle")}
                            description={localModeUnavailable}
                        />
                    ) : (
                        <Local />
                    )}
                    <Wireguard />
                    <Reverse />
                </div>
            </div>
            <div className="modes-category gray-left-border">
                <h3>{t("modes.advanced")}</h3>
                <div className="modes-container">
                    <Socks />
                    <Upstream />
                    <Dns />
                    {!platform.startsWith("win32") ? (
                        <Transparent />
                    ) : (
                        <MissingMode
                            title={t("modes.transparent.title")}
                            description={t("modes.transparentMissingDescription")}
                        />
                    )}
                </div>
            </div>
        </div>
    );
}
