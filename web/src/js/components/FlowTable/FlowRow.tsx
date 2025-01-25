import React, { useCallback } from "react";
import classnames from "classnames";
import { Flow } from "../../flow";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { select } from "../../ducks/flows";
import * as columns from "./FlowColumns";

type FlowRowProps = {
    flow: Flow;
    selected: boolean;
    highlighted: boolean;
};

export default React.memo(function FlowRow({
    flow,
    selected,
    highlighted,
}: FlowRowProps) {
    const dispatch = useAppDispatch();
    const displayColumnNames = useAppSelector(
        (state) => state.options.web_columns,
    );
    const className = classnames({
        selected: selected,
        highlighted: highlighted,
        intercepted: flow.intercepted,
        "has-request": flow.type === "http" && flow.request,
        "has-response": flow.type === "http" && flow.response,
    });

    const onClick = useCallback(
        (e) => {
            // a bit of a hack to disable row selection for quickactions.
            let node = e.target;
            while (node.parentNode) {
                if (node.classList.contains("col-quickactions")) return;
                node = node.parentNode;
            }
            dispatch(select(flow.id));
        },
        [flow],
    );

    const displayColumns = displayColumnNames
        .map((x) => columns[x])
        .filter((x) => x)
        .concat(columns.quickactions);

    return (
        <tr className={className} onClick={onClick}>
            {displayColumns.map((Column) => (
                <Column key={Column.name} flow={flow} />
            ))}
        </tr>
    );
});
