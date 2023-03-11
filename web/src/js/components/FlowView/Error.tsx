import { HTTPFlow } from "../../flow";
import { formatTimeStamp } from "../../utils";
import * as React from "react";

type ErrorProps = {
    flow: HTTPFlow & { error: Error };
};

export default function Error({ flow }: ErrorProps) {
    return (
        <section className="error">
            <div className="alert alert-warning">
                {flow.error.msg}
                <div>
                    <small>{formatTimeStamp(flow.error.timestamp)}</small>
                </div>
            </div>
        </section>
    );
}
Error.displayName = "Error";
