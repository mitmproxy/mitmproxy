import type { Flow } from "../../flow";
import * as React from "react";
import { useTranslation } from "react-i18next";
import { formatTimeStamp, formatTimeDelta } from "../../utils";

export type TimeStampProps = {
    ts: number;
    deltaTo?: number;
    title: string;
};

export function TimeStamp({ ts, deltaTo, title }: TimeStampProps) {
    return ts ? (
        <tr>
            <td>{title}:</td>
            <td>
                {formatTimeStamp(ts)}
                {deltaTo && (
                    <span className="text-muted">
                        ({formatTimeDelta(1000 * (ts - deltaTo))})
                    </span>
                )}
            </td>
        </tr>
    ) : (
        <tr />
    );
}

export default function Timing({ flow }: { flow: Flow }) {
    const { t } = useTranslation();
    let ref: number;
    if (flow.type === "http") {
        ref = flow.request.timestamp_start;
    } else {
        ref = flow.client_conn.timestamp_start;
    }

    const timestamps: { titleKey: string; ts: number | undefined; deltaTo?: number }[] = [
        { titleKey: "serverConnInitiated", ts: flow.server_conn?.timestamp_start, deltaTo: ref },
        { titleKey: "serverConnTcpHandshake", ts: flow.server_conn?.timestamp_tcp_setup, deltaTo: ref },
        { titleKey: "serverConnTlsHandshake", ts: flow.server_conn?.timestamp_tls_setup, deltaTo: ref },
        { titleKey: "serverConnClosed", ts: flow.server_conn?.timestamp_end, deltaTo: ref },
        { titleKey: "clientConnEstablished", ts: flow.client_conn.timestamp_start, deltaTo: flow.type === "http" ? ref : undefined },
        { titleKey: "clientConnTlsHandshake", ts: flow.client_conn.timestamp_tls_setup, deltaTo: ref },
        { titleKey: "clientConnClosed", ts: flow.client_conn.timestamp_end, deltaTo: ref },
    ];
    if (flow.type === "http") {
        timestamps.push(
            { titleKey: "firstRequestByte", ts: flow.request.timestamp_start },
            { titleKey: "requestComplete", ts: flow.request.timestamp_end, deltaTo: ref },
            { titleKey: "firstResponseByte", ts: flow.response?.timestamp_start, deltaTo: ref },
            { titleKey: "responseComplete", ts: flow.response?.timestamp_end, deltaTo: ref },
        );
    }

    return (
        <section className="timing">
            <h4>{t("flowView.timing.title")}</h4>
            <table className="timing-table">
                <tbody>
                    {timestamps
                        .filter((v): v is { titleKey: string; ts: number; deltaTo?: number } => !!v.ts)
                        .sort((a, b) => a.ts - b.ts)
                        .map(({ titleKey, ts, deltaTo }) => (
                            <TimeStamp
                                key={titleKey}
                                title={t(`flowView.timing.${titleKey}`)}
                                ts={ts}
                                deltaTo={deltaTo}
                            />
                        ))}
                </tbody>
            </table>
        </section>
    );
}
Timing.displayName = "Timing";
