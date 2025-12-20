import * as React from "react";
import classnames from "classnames";
import FlowColumns from "./FlowColumns";

import { setSort } from "../../ducks/flows";
import { useAppDispatch, useAppSelector } from "../../ducks";
import { isValidColumnName } from "../../flow/utils";

export default React.memo(function FlowTableHead() {
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
                    {FlowColumns[colName].headerName}
                </th>
            ))}
        </tr>
    );
});
