import * as React from "react";
import classnames from "classnames";
import FlowColumns from "./FlowColumns";
import Icon from "../common/Icon";

import { setSort } from "../../ducks/flows";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { isValidColumnName } from "../../flow/utils";

const MIN_COLUMN_WIDTH = 20;

type FlowTableHeadProps = {
    onResize: (widths: Record<string, number>) => void;
    onResizeEnd: (widths: Record<string, number>) => void;
};

export default React.memo(function FlowTableHead({
    onResize,
    onResizeEnd,
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

    // The actions column holds buttons, so there is nothing to order it by.
    const sortBy = (colName: (typeof displayColumns)[number]) =>
        colName === "quickactions"
            ? undefined
            : () =>
                  dispatch(
                      setSort({
                          column:
                              colName === sortColumn && sortDesc
                                  ? undefined
                                  : colName,
                          desc: colName !== sortColumn ? false : !sortDesc,
                      }),
                  );

    const startResize = (colName: string) => (e: React.PointerEvent) => {
        // Don't let the resize gesture trigger a column sort.
        e.preventDefault();
        e.stopPropagation();

        const handle = e.currentTarget as HTMLElement;

        // Fixed table layout hands the space the sized columns leave over to every column without a width of its own, so setting one width on its own shifts the rest too.
        // Pinning them all keeps the handle under the cursor; `quickactions` is left out and takes the slack instead.
        const cells = handle.closest("tr")!.children;
        const widths = Object.fromEntries(
            displayColumns
                .filter((col) => col !== "quickactions")
                .map((col, i): [string, number] => [
                    col,
                    (cells[i] as HTMLElement).offsetWidth,
                ]),
        );
        onResize(widths);

        handle.setPointerCapture(e.pointerId);
        document.body.classList.add("resizing-columns");

        const startX = e.clientX;
        const startWidth = widths[colName];
        const abort = new AbortController();
        const { signal } = abort;

        // Pointers sample faster than the display refreshes, so coalesce moves into one update per frame.
        let frame = 0,
            clientX = startX;
        const currentWidth = () => ({
            [colName]: Math.max(
                MIN_COLUMN_WIDTH,
                startWidth + clientX - startX,
            ),
        });
        const apply = () => {
            frame = 0;
            onResize(currentWidth());
        };
        const onUp = () => {
            cancelAnimationFrame(frame);
            abort.abort();
            document.body.classList.remove("resizing-columns");
            // The final width goes through the end callback rather than onResize, so persistence and re-measurement see it instead of the frame before.
            onResizeEnd(currentWidth());
        };
        document.addEventListener(
            "pointermove",
            (ev: PointerEvent) => {
                clientX = ev.clientX;
                if (!frame) frame = requestAnimationFrame(apply);
            },
            { signal },
        );
        document.addEventListener("pointerup", onUp, { signal });
        document.addEventListener("pointercancel", onUp, { signal });
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
                    onClick={sortBy(colName)}
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
            <th className="col-filler" />
        </tr>
    );
});
