import * as React from "react";
import { useAppSelector } from "../../ducks";

export default function Metadata() {
    const flow = useAppSelector(
        (state) => state.flows.byId[state.flows.selected[0]]
    );

    return (
        <section>
            <pre>{JSON.stringify(flow.metadata,null,4)}</pre>
        </section>
    );
}

Metadata.displayName = "Metadata";
