import { Flow } from "../../flow";
import * as React from "react";
import { formatTimeDelta, formatTimeStamp } from "../../utils";

export type TimeStampProps = {
    t: number;
    deltaTo?: number;
    title: string;
};

export function TimeStamp({ t, deltaTo, title }: TimeStampProps) {
    return t ? (
        <tr>
            <td>{title}:</td>
            <td>
                {formatTimeStamp(t)}
                {deltaTo && (
                    <span className="text-muted">
                        ({formatTimeDelta(1000 * (t - deltaTo))})
                    </span>
                )}
            </td>
        </tr>
    ) : (
        <tr />
    );
}

export default function Timing({ flow }: { flow: Flow }) {
    let ref: number;
    if (flow.type === "http") {
        ref = flow.request.timestamp_start;
    } else {
        ref = flow.client_conn.timestamp_start;
    }

    const timestamps: Partial<TimeStampProps>[] = [
        {
            title: "Server conn. initiated",
            t: flow.server_conn?.timestamp_start,
            deltaTo: ref,
        },
        {
            title: "Server conn. TCP handshake",
            t: flow.server_conn?.timestamp_tcp_setup,
            deltaTo: ref,
        },
        {
            title: "Server conn. TLS handshake",
            t: flow.server_conn?.timestamp_tls_setup,
            deltaTo: ref,
        },
        {
            title: "Server conn. closed",
            t: flow.server_conn?.timestamp_end,
            deltaTo: ref,
        },
        {
            title: "Client conn. established",
            t: flow.client_conn.timestamp_start,
            deltaTo: flow.type === "http" ? ref : undefined,
        },
        {
            title: "Client conn. TLS handshake",
            t: flow.client_conn.timestamp_tls_setup,
            deltaTo: ref,
        },
        {
            title: "Client conn. closed",
            t: flow.client_conn.timestamp_end,
            deltaTo: ref,
        },
    ];
    if (flow.type === "http") {
        timestamps.push(
            ...[
                {
                    title: "First request byte",
                    t: flow.request.timestamp_start,
                },
                {
                    title: "Request complete",
                    t: flow.request.timestamp_end,
                    deltaTo: ref,
                },
                {
                    title: "First response byte",
                    t: flow.response?.timestamp_start,
                    deltaTo: ref,
                },
                {
                    title: "Response complete",
                    t: flow.response?.timestamp_end,
                    deltaTo: ref,
                },
            ],
        );
    }

    return (
        <section className="timing">
            <h4>Timing</h4>
            <table className="timing-table">
                <tbody>
                    {timestamps
                        .filter((v): v is TimeStampProps => !!v.t)
                        .sort((a, b) => a.t - b.t)
                        .map(({ title, t, deltaTo }) => (
                            <TimeStamp
                                key={title}
                                title={title}
                                t={t}
                                deltaTo={deltaTo}
                            />
                        ))}
                </tbody>
            </table>
        </section>
    );
}
Timing.displayName = "Timing";
