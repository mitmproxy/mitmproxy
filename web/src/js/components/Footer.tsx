import * as React from "react";
import { useTranslation } from "react-i18next";
import { formatSize } from "../utils";
import HideInStatic from "../components/common/HideInStatic";
import { useAppSelector } from "../ducks";

export default function Footer() {
    const { t } = useTranslation();
    const version = useAppSelector((state) => state.backendState.version);
    const {
        mode,
        intercept,
        showhost,
        upstream_cert,
        rawtcp,
        http2,
        websocket,
        anticache,
        anticomp,
        stickyauth,
        stickycookie,
        stream_large_bodies,
        listen_host,
        listen_port,
        server,
        ssl_insecure,
    } = useAppSelector((state) => state.options);

    const selectedFlowsLength = useAppSelector(
        (state) => state.flows.selected.length,
    );
    const totalFlowsLength = useAppSelector((state) => state.flows.list.length);

    return (
        <footer>
            {mode && (mode.length !== 1 || mode[0] !== "regular") && (
                <span className="label label-success">{mode.join(",")}</span>
            )}
            {intercept && (
                <span className="label label-success">
                    {t("footer.intercept", { value: intercept })}
                </span>
            )}
            {ssl_insecure && (
                <span className="label label-danger">{t("footer.sslInsecure")}</span>
            )}
            {showhost && <span className="label label-success">{t("footer.showhost")}</span>}
            {!upstream_cert && (
                <span className="label label-success">{t("footer.noUpstreamCert")}</span>
            )}
            {!rawtcp && <span className="label label-success">{t("footer.noRawTcp")}</span>}
            {!http2 && <span className="label label-success">{t("footer.noHttp2")}</span>}
            {!websocket && (
                <span className="label label-success">{t("footer.noWebsocket")}</span>
            )}
            {anticache && (
                <span className="label label-success">{t("footer.anticache")}</span>
            )}
            {anticomp && <span className="label label-success">{t("footer.anticomp")}</span>}
            {stickyauth && (
                <span className="label label-success">
                    {t("footer.stickyauth", { value: stickyauth })}
                </span>
            )}
            {stickycookie && (
                <span className="label label-success">
                    {t("footer.stickycookie", { value: stickycookie })}
                </span>
            )}
            {stream_large_bodies && (
                <span className="label label-success">
                    {t("footer.stream", { value: formatSize(stream_large_bodies) })}
                </span>
            )}
            {totalFlowsLength > 0 && (
                <span className="label label-default">
                    {t("footer.flowsSelected", { selected: selectedFlowsLength, total: totalFlowsLength })}
                </span>
            )}
            <div className="pull-right">
                <HideInStatic>
                    {server && (
                        <span
                            className="label label-primary"
                            title={t("footer.proxyAddressTitle")}
                        >
                            {listen_host || "*"}:{listen_port || 8080}
                        </span>
                    )}
                </HideInStatic>
                <span className="label label-default" title={t("footer.versionTitle")}>
                    mitmproxy {version}
                </span>
            </div>
        </footer>
    );
}
