import * as React from "react";
import classnames from "classnames";

export function statusClass(code: string | number): string {
    const n = typeof code === "number" ? code : parseInt(code, 10);
    if (Number.isNaN(n)) return "status-other";
    if (n >= 100 && n < 200) return "status-1xx";
    if (n >= 200 && n < 300) return "status-2xx";
    if (n >= 300 && n < 400) return "status-3xx";
    if (n >= 400 && n < 500) return "status-4xx";
    if (n >= 500 && n < 600) return "status-5xx";
    return "status-other";
}

export default function StatusBadge({ code }: { code: string | number }) {
    return (
        <span className={classnames("status-badge", statusClass(code))}>
            {code}
        </span>
    );
}
