import * as React from "react";
import { useTranslation } from "react-i18next";
import { ConnectionState } from "../../ducks/connection";
import { useAppSelector } from "../../ducks";
import { assertNever } from "../../utils";

export default React.memo(
    function ConnectionIndicator(): React.ReactElement<any> {
        const { t } = useTranslation();
        const connState = useAppSelector((state) => state.connection.state);
        const message = useAppSelector((state) => state.connection.message);

        switch (connState) {
            case ConnectionState.INIT:
                return (
                    <span className="connection-indicator init">
                        {t("header.connectionIndicator.connecting")}
                    </span>
                );
            case ConnectionState.FETCHING:
                return (
                    <span className="connection-indicator fetching">
                        {t("header.connectionIndicator.fetchingData")}
                    </span>
                );
            case ConnectionState.ESTABLISHED:
                return (
                    <span className="connection-indicator established">
                        {t("header.connectionIndicator.connected")}
                    </span>
                );
            case ConnectionState.ERROR:
                return (
                    <span
                        className="connection-indicator error"
                        title={message}
                    >
                        {t("header.connectionIndicator.connectionLost")}
                    </span>
                );
            /* istanbul ignore next @preserve */
            default:
                assertNever(connState);
        }
    },
);
