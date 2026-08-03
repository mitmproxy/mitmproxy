import React, { useCallback } from "react";
import classnames from "classnames";
import type { Flow } from "../../flow";
import { useAppDispatch } from "../../ducks";
import { select, selectRange, selectToggle } from "../../ducks/flows";
import { isValidColumnName } from "../../flow/utils";
import * as columns from "./FlowColumns";

type FlowRowProps = {
    flow: Flow;
    selected: boolean;
    highlighted: boolean;
    displayColumnNames: string[];
    rowNumber: number;
    height: number;
};

export default React.memo(function FlowRow({
    flow,
    selected,
    highlighted,
    displayColumnNames,
    rowNumber,
    height,
}: FlowRowProps) {
    const dispatch = useAppDispatch();
    const className = classnames({
        selected,
        highlighted,
        intercepted: flow.intercepted,
        "has-request": flow.type === "http" && flow.request,
        "has-response": flow.type === "http" && flow.response,
    });

    const onClick = useCallback(
        (e: React.MouseEvent<HTMLTableRowElement>) => {
            // The quickaction buttons act on the flow themselves; the rest of their column selects the row like any other cell.
            if ((e.target as HTMLElement).closest(".quickaction")) return;
            if (e.metaKey || e.ctrlKey) {
                dispatch(selectToggle(flow));
            } else if (e.shiftKey) {
                window.getSelection()?.empty();
                dispatch(selectRange(flow));
            } else {
                dispatch(select([flow]));
            }
        },
        [flow],
    );

    const displayColumns = displayColumnNames
        .filter(isValidColumnName)
        .map((x) => columns[x])
        .concat(columns.quickactions);

    return (
        <tr className={className} onClick={onClick} style={{ height }}>
            {displayColumns.map((Column) => (
                <Column key={Column.name} flow={flow} rowNumber={rowNumber} />
            ))}
            {/* Empty, but without a cell the row stops painting its background where the filler column starts. */}
            <td className="col-filler" />
        </tr>
    );
});
