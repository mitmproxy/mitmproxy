import React, { useCallback } from "react";
import classnames from "classnames";
import { Flow } from "../../flow";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { select } from "../../ducks/flows";
import * as columns from "./FlowColumns";

type FlowRowProps = {
    flow: Flow;
    isSelected: boolean;
    isHighlighted: boolean;
};

export default React.memo(function FlowRow({
    flow,
    isSelected,
    isHighlighted,
}: FlowRowProps) {
    const dispatch = useAppDispatch();
    const displayColumnNames = useAppSelector(
        (state) => state.options.web_columns,
    );
    const selectedFlowIds = useAppSelector((state) => state.flows.selected); // used for multiple flows selection
    const className = classnames({
        selected: isSelected,
        highlighted: isHighlighted,
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
            if (e.metaKey || e.ctrlKey) {
                if (selectedFlowIds.includes(flow.id)) {
                    // If the flow is already selected, remove it.
                    dispatch(
                        select(selectedFlowIds.filter((id) => id !== flow.id)),
                    );
                } else {
                    dispatch(select([...selectedFlowIds, flow.id]));
                }
            } else {
                // select only the clicked flow
                dispatch(select([flow.id]));
            }
        },
        [flow, selectedFlowIds],
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
