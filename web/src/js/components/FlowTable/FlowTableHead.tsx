import * as React from "react";
import classnames from "classnames";
import FlowColumns from "./FlowColumns";
import Icon from "../common/Icon";

import { setSort } from "../../ducks/flows";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { isValidColumnName } from "../../flow/utils";

const MIN_COLUMN_WIDTH = 20;

type FlowTableHeadProps = {
    columnWidths: Record<string, number>;
    onResize: (column: string, width: number) => void;
};

export default React.memo(function FlowTableHead({
    columnWidths,
    onResize,
}: FlowTableHeadProps) {
    const dispatch = useAppDispatch();
    const sortDesc = useAppSelector((state) => state.flows.sort.desc);
    const sortColumn = useAppSelector((state) => state.flows.sort.column);
    const displayColumnNames = useAppSelector(
        (state) => state.options.web_columns,
    );

    const sortType = sortDesc ? "sort-desc" : "sort-asc";
    const displayColumns = displayColumnNames
        .filter(isValidColumnName)
        .concat("quickactions");

    const startResize = (colName: string) => (e: React.PointerEvent) => {
        // Don't let the resize gesture trigger a column sort.
        e.preventDefault();
        e.stopPropagation();
        const th = (e.currentTarget as HTMLElement).closest("th");
        const startX = e.clientX;
        const startWidth = columnWidths[colName] ?? th?.offsetWidth ?? 0;

        const onMove = (ev: PointerEvent) => {
            onResize(
                colName,
                Math.max(MIN_COLUMN_WIDTH, startWidth + (ev.clientX - startX)),
            );
        };
        const onUp = () => {
            document.removeEventListener("pointermove", onMove);
            document.removeEventListener("pointerup", onUp);
        };
        document.addEventListener("pointermove", onMove);
        document.addEventListener("pointerup", onUp);
    };

    return (
        <tr>
            {displayColumns.map((colName) => (
                <th
                    className={classnames(
                        `col-${colName}`,
                        sortColumn === colName && sortType,
                    )}
                    key={colName}
                    onClick={() =>
                        dispatch(
                            setSort({
                                column:
                                    colName === sortColumn && sortDesc
                                        ? undefined
                                        : colName,
                                desc:
                                    colName !== sortColumn ? false : !sortDesc,
                            }),
                        )
                    }
                >
                    <span className="th-content">
                        {FlowColumns[colName].headerName}
                    </span>
                    {sortColumn === colName && (
                        <Icon
                            strokeWidth={3}
                            name={sortDesc ? "chevronDown" : "chevronUp"}
                            className="sort-indicator"
                        />
                    )}
                    {colName !== "quickactions" && (
                        <span
                            className="col-resize-handle"
                            onPointerDown={startResize(colName)}
                            onClick={(e) => e.stopPropagation()}
                        />
                    )}
                </th>
            ))}
        </tr>
    );
});
