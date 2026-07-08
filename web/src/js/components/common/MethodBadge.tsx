import * as React from "react";

export default function MethodBadge({ method }: { method: string }) {
    return <span className="method-badge">{method}</span>;
}
