import { Flow } from "../../flow";
import * as React from "react";
import { formatTimeDelta, formatTimeStamp } from "../../utils";
import { useAppSelector } from "../../../ducks/hooks"; // Correct import path

export type TimeStampProps = {
    t: number;
    deltaTo?: number;
    title: string;
};

export function TimeStamp({
    t,
    deltaTo,
    title,
    timezone,
}: TimeStampProps & { timezone: "utc" | "local" }) {
    if (!t) return null;

    return (
        <tr>
            <td>{title}:</td>
            <td>
                {formatTimeStamp(t, { timezone })}
                {deltaTo && (
                    <span className="text-muted">
                        ({formatTimeDelta(1000 * (t - deltaTo))})
                    </span>
                )}
            </td>
        </tr>
    );
}

export default function Timing({ flow }: { flow: Flow }) {
    // Determine reference timestamp
    const ref =
        flow.type === "http"
            ? flow.request.timestamp_start
            : flow.client_conn.timestamp_start;

    // Build timestamps array
    const timestamps: (Partial<TimeStampProps> & { t?: number })[] = [
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

    // Add HTTP-specific timestamps
    if (flow.type === "http") {
        timestamps.push(
            { title: "First request byte", t: flow.request.timestamp_start },
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
        );
    }

    // Get timezone setting from Redux - CORRECT PATH
    const timezoneDisplay = useAppSelector(
        (state) => state.ui.preferences.timezoneDisplay,
    );

    // Filter and sort valid timestamps
    const validTimestamps = timestamps
        .filter((v): v is TimeStampProps => !!v.t)
        .sort((a, b) => a.t - b.t);

    return (
        <section className="timing">
            <h4>Timing</h4>
            <table className="timing-table">
                <tbody>
                    {validTimestamps.map(({ title, t, deltaTo }) => (
                        <TimeStamp
                            key={title}
                            title={title}
                            t={t}
                            deltaTo={deltaTo}
                            timezone={timezoneDisplay}
                        />
                    ))}
                </tbody>
            </table>
        </section>
    );
}

Timing.displayName = "Timing";
