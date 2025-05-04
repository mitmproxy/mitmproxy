import * as React from "react";
import classnames from "classnames";
import * as columns from "./FlowColumns";

import { setSort } from "../../ducks/flows";
import { useAppDispatch, useAppSelector } from "../../ducks";

export default React.memo(function FlowTableHead() {
    const dispatch = useAppDispatch();
    const sortDesc = useAppSelector((state) => state.flows.sort.desc);
    const sortColumn = useAppSelector((state) => state.flows.sort.column);
    const displayColumnNames = useAppSelector(
        (state) => state.options.web_columns,
    );

    const sortType = sortDesc ? "sort-desc" : "sort-asc";
    const displayColumns = displayColumnNames
        .map((x) => columns[x])
        .filter((x) => x)
        .concat(columns.quickactions);

    return (
        <tr>
            {displayColumns.map((Column) => (
                <th
                    className={classnames(
                        `col-${Column.name}`,
                        sortColumn === Column.name && sortType,
                    )}
                    key={Column.name}
                    onClick={() =>
                        dispatch(
                            setSort({
                                column:
                                    Column.name === sortColumn && sortDesc
                                        ? undefined
                                        : Column.name,
                                desc:
                                    Column.name !== sortColumn
                                        ? false
                                        : !sortDesc,
                            }),
                        )
                    }
                >
                    {Column.headerName}
                </th>
            ))}
        </tr>
    );
});
